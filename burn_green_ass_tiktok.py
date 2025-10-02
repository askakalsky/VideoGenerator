import argparse
import math
import subprocess
import json
from pathlib import Path

import stable_whisper  # stable-ts
import pysubs2
from pathlib import Path


from pathlib import Path


def escape_for_subtitles_filter(p: str) -> str:
    # POSIX-путь + экранирование двоеточий для ffmpeg фильтра
    return Path(p).resolve().as_posix().replace(":", r"\:")


def build_subtitles_filter_arg(ass_path: str, fontsdir: str | None = None) -> str:
    ass_esc = escape_for_subtitles_filter(ass_path)
    vf = f"subtitles=filename={ass_esc}"
    if fontsdir:
        fonts_esc = escape_for_subtitles_filter(fontsdir)
        vf += f":fontsdir={fonts_esc}"
    return vf


def run(cmd, cwd=None):
    subprocess.run(cmd, check=True, cwd=cwd)


def ffprobe_video_size(path: str) -> tuple[int, int]:
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json",
        path
    ]
    p = subprocess.run(cmd, check=True, capture_output=True, text=True)
    data = json.loads(p.stdout)
    stream = data["streams"][0]
    return int(stream["width"]), int(stream["height"])


def sec_to_ms(s: float | None) -> int:
    if s is None or math.isnan(s):
        return 0
    return int(round(s * 1000))


def to_ass_bgr(hex_color: str) -> str:
    c = hex_color.strip().lstrip("#")
    if len(c) != 6:
        raise ValueError(f"Цвет должен быть #RRGGBB, а не {hex_color}")
    r, g, b = c[0:2], c[2:4], c[4:6]
    return f"{b}{g}{r}"


def escape_ass(text: str) -> str:
    return text.replace("\\", r"\\").replace("\n", r"\N").replace("\r", "")


def ffmpeg_escape_for_filter(path: Path) -> str:
    s = path.resolve().as_posix()
    return s.replace(":", r"\:")


def transcribe_stable_ts(media_path: str, model: str, language: str | None, device: str | None, vad: bool):
    model_obj = stable_whisper.load_model(model, device=device)
    result = model_obj.transcribe(
        media_path,
        word_timestamps=True,
        vad=vad,
        language=language,
    )
    return result


def build_ass_with_word_highlight(
    result,
    ass_path: str,
    video_w: int,
    video_h: int,
    green="#00FF6A",
    white="#FFFFFF",
    font_name="Arial",
    font_scale=0.07,
    margin_v_ratio=0.13,
    margin_lr_ratio=0.06,
    outline_ratio=0.003,
    shadow_ratio=0.0,
    align=2
):
    subs = pysubs2.SSAFile()

    # Привязываем координатную сетку сценария к реальному разрешению видео
    subs.info["PlayResX"] = video_w
    subs.info["PlayResY"] = video_h
    subs.info["ScaledBorderAndShadow"] = "yes"

    # Относительные параметры -> абсолютные
    font_size = max(12, int(round(video_h * font_scale)))
    margin_v = max(0, int(round(video_h * margin_v_ratio)))
    margin_l = max(0, int(round(video_w * margin_lr_ratio)))
    margin_r = margin_l
    outline = max(1, int(round(video_h * outline_ratio)))
    shadow = int(round(video_h * shadow_ratio))

    # Базовый стиль
    style = pysubs2.SSAStyle()
    style.name = "TikTok"
    style.fontname = font_name
    style.fontsize = font_size
    style.primarycolor = pysubs2.Color(255, 255, 255, 0)  # белый
    style.secondarycolor = pysubs2.Color(255, 255, 255, 0)
    style.outlinecolor = pysubs2.Color(0, 0, 0, 0)        # чёрный контур
    style.backcolor = pysubs2.Color(0, 0, 0, 0)
    style.bold = False
    style.italic = False
    style.underline = False
    style.strikeout = False
    style.scale_x = 100
    style.scale_y = 100
    style.spacing = 0
    style.angle = 0
    style.borderstyle = 1
    style.outline = outline
    style.shadow = shadow
    style.alignment = align
    style.marginl = margin_l
    style.marginr = margin_r
    style.marginv = margin_v

    subs.styles["TikTok"] = style

    green_ass = to_ass_bgr(green)
    white_ass = to_ass_bgr(white)

    def get_attr(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    segments = get_attr(result, "segments", [])
    for seg in segments:
        seg_start = get_attr(seg, "start", None)
        seg_end = get_attr(seg, "end", None)
        words = get_attr(seg, "words", []) or []

        if not words:
            text = escape_ass(get_attr(seg, "text", "").strip())
            if text and seg_start is not None and seg_end is not None:
                subs.events.append(
                    pysubs2.SSAEvent(start=sec_to_ms(seg_start),
                                     end=sec_to_ms(seg_end),
                                     text=text,
                                     style="TikTok")
                )
            continue

        # Собираем слова с валидными таймингами
        timed_words = []
        for w in words:
            w_start = get_attr(w, "start")
            w_end = get_attr(w, "end")
            w_text = get_attr(w, "word", "").strip()
            if w_start is not None and w_end is not None and w_text:
                timed_words.append({
                    "start": w_start,
                    "end": w_end,
                    "text": w_text,
                    "original": w
                })

        if not timed_words:
            full_text = escape_ass(
                "".join(get_attr(w, "word", "") for w in words).strip())
            if full_text and seg_start is not None and seg_end is not None:
                subs.events.append(
                    pysubs2.SSAEvent(start=sec_to_ms(seg_start),
                                     end=sec_to_ms(seg_end),
                                     text=full_text,
                                     style="TikTok")
                )
            continue

        # ВАЖНО: Создаём НЕперекрывающиеся события
        for i, tw in enumerate(timed_words):
            # Определяем точное время начала и конца для этого события
            event_start = tw["start"]

            # Конец события = начало следующего слова (чтобы не было перекрытий)
            if i + 1 < len(timed_words):
                event_end = timed_words[i + 1]["start"]
            else:
                # Для последнего слова используем его собственный конец или конец сегмента
                event_end = max(
                    tw["end"], seg_end if seg_end is not None else tw["end"])

            # Защита от нулевой длительности
            if event_end <= event_start:
                event_end = event_start + 0.1

            # Строим текст со всеми словами, но подсвечиваем только текущее
            parts = [f"{{\\c&H{white_ass}&}}"]
            for j, w in enumerate(words):
                token_text = escape_ass(get_attr(w, "word", ""))
                if not token_text:
                    continue

                # Проверяем, это текущее слово или нет
                is_current = False
                if j < len(words):
                    # Сравниваем по тексту и примерному времени
                    w_start = get_attr(w, "start")
                    if (w_start is not None and
                        abs(w_start - tw["start"]) < 0.01 and
                            token_text.strip() == tw["text"]):
                        is_current = True

                if is_current:
                    parts.append(
                        f"{{\\c&H{green_ass}&}}{token_text}{{\\c&H{white_ass}&}}")
                else:
                    parts.append(token_text)

            line = "".join(parts)

            subs.events.append(
                pysubs2.SSAEvent(
                    start=sec_to_ms(event_start),
                    end=sec_to_ms(event_end),
                    text=line,
                    style="TikTok"
                )
            )

    subs.save(ass_path)


def burn_ass_to_video(input_video: str, ass_path: str, output_video: str,
                      crf=18, preset="medium", audio_codec="aac",
                      fontsdir: str | None = None):
    # 1) Работаем из папки, где лежит .ass (чтобы в -vf использовать относительные пути без двоеточий)
    ass_p = Path(ass_path).resolve()
    workdir = ass_p.parent
    ass_name = ass_p.name  # например, "out.ass"

    # 2) Строим фильтр без абсолютных путей и без кавычек
    # Для ASS-файла используем фильтр 'ass' (специализирован под .ass)
    vf = f"ass={ass_name}"

    # 3) Если указан fontsdir — превращаем в относительный путь к workdir
    if fontsdir:
        try:
            fonts_rel = Path(fontsdir).resolve().relative_to(workdir)
            # относительный путь со слешами
            fonts_rel = fonts_rel.as_posix()
        except Exception:
            # если fontsdir на другом диске или не получается посчитать относительный —
            # пробуем через os.path.relpath; если и это на другом диске — просто предупредим и отключим fontsdir
            try:
                import os
                fonts_rel = os.path.relpath(
                    Path(fontsdir).resolve(), workdir).replace("\\", "/")
            except Exception:
                print("Внимание: --fontsdir на другом диске. "
                      "Скопируй шрифты рядом с .ass и передай относительный путь, например --fontsdir fonts")
                fonts_rel = None

        if fonts_rel:
            vf += f":fontsdir={fonts_rel}"

    cmd = [
        "ffmpeg", "-y",
        # видео можно передать абсолютным путём
        "-i", str(Path(input_video).resolve()),
        "-vf", vf,                               # а здесь — только относительные пути
        "-c:v", "libx264", "-crf", str(crf), "-preset", preset,
        "-c:a", audio_codec,
        "-movflags", "+faststart",
        str(Path(output_video).resolve())
    ]
    print("Running:", " ".join(cmd))
    # 4) Запускаем ffmpeg из папки .ass — тогда "ass=out.ass" точно найдётся
    subprocess.run(cmd, check=True, cwd=str(workdir))


def main():
    ap = argparse.ArgumentParser(
        description="Бегущая зелёная подсветка по словам. Масштаб под размер 9:16-видео.")
    ap.add_argument("-i", "--input", required=True, help="Видео (mp4/mov/...)")
    ap.add_argument("-o", "--output", required=True, help="Финальный mp4")
    ap.add_argument("--model", default="small",
                    help="Модель stable-ts/Whisper (tiny/small/medium/large-v2/...)")
    ap.add_argument("--language", default=None,
                    help="Язык (ru/en/...), если None — авто")
    ap.add_argument("--device", default=None, help="cuda/cpu")
    ap.add_argument("--no-vad", action="store_true", help="Отключить VAD")
    # Визуальные опции
    ap.add_argument("--green", default="#00FF6A", help="Цвет текущего слова")
    ap.add_argument("--white", default="#FFFFFF", help="Цвет остальных слов")
    ap.add_argument("--font", default="Arial",
                    help="Имя шрифта (как видит libass)")
    ap.add_argument("--fontsdir", default=None,
                    help="Папка со шрифтами для libass (укажи, если используешь кастомный .ttf)")
    # Относительные параметры (относительно высоты/ширины видео)
    ap.add_argument("--font-scale", type=float, default=0.07,
                    help="Размер шрифта как доля высоты (напр., 0.07 = 7%)")
    ap.add_argument("--marginv", type=float, default=0.13,
                    help="Нижний отступ как доля высоты (напр., 0.13 = 13%)")
    ap.add_argument("--marginlr", type=float, default=0.06,
                    help="Лев./прав. отступы как доля ширины")
    ap.add_argument("--outline", type=float, default=0.003,
                    help="Толщина контура как доля высоты")
    ap.add_argument("--shadow", type=float, default=0.0,
                    help="Тень как доля высоты")
    args = ap.parse_args()

    # 1) Получаем размер видео
    vw, vh = ffprobe_video_size(args.input)

    # 2) Транскрибируем
    result = transcribe_stable_ts(
        media_path=args.input,
        model=args.model,
        language=args.language,
        device=args.device,
        vad=not args.no_vad
    )

    # 3) Генерируем .ass со стилем, масштабированным под реальный размер видео
    ass_path = str(Path(args.output).with_suffix(".ass"))
    build_ass_with_word_highlight(
        result,
        ass_path=ass_path,
        video_w=vw,
        video_h=vh,
        green=args.green,
        white=args.white,
        font_name=args.font,
        font_scale=args.font_scale,
        margin_v_ratio=args.marginv,
        margin_lr_ratio=args.marginlr,
        outline_ratio=args.outline,
        shadow_ratio=args.shadow,
        align=2
    )

    # 4) Прожигаем субтитры
    burn_ass_to_video(
        input_video=args.input,
        ass_path=ass_path,
        output_video=args.output,
        fontsdir=args.fontsdir
    )

    print(f"Готово: {Path(args.output).resolve()}")
    print(f"ASS:    {Path(ass_path).resolve()}")


if __name__ == "__main__":
    main()
