from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr
from zipfile import ZIP_DEFLATED, ZipFile
from zoneinfo import ZoneInfo

WORD = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
OFFICE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE = "http://schemas.openxmlformats.org/package/2006/relationships"
PICTURE = "http://schemas.openxmlformats.org/drawingml/2006/picture"
DRAW = "http://schemas.openxmlformats.org/drawingml/2006/main"
WORD_DRAW = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"

SCREENSHOTS = (
    ("01-register.jpg", "Форма регистрации."),
    ("02-captcha-error.jpg", "Вход с неверным кодом. Django показывает ошибку и новую капчу."),
    ("03-profile.jpg", "Личный кабинет после успешного входа тестового пользователя."),
)
GROUPS = (
    ("RegistrationTests", "Регистрация"),
    ("LoginTests", "Вход и капча"),
    ("ProfileTests", "Личный кабинет"),
)


def paragraph(value, *, bold=False, center=False, size=24, keep=False, before=0, font="Times New Roman"):
    align = '<w:jc w:val="center"/>' if center else ""
    keep_next = "<w:keepNext/>" if keep else ""
    weight = "<w:b/>" if bold else ""
    lines = '<w:br/>'.join(
        f'<w:t xml:space="preserve">{escape(line)}</w:t>' for line in value.split("\n")
    )
    return (
        f'<w:p><w:pPr>{keep_next}<w:spacing w:before="{before}" w:after="100"/>{align}</w:pPr>'
        f'<w:r><w:rPr><w:rFonts w:ascii="{font}" w:hAnsi="{font}"/>{weight}'
        f'<w:sz w:val="{size}"/><w:lang w:val="ru-RU"/></w:rPr>{lines}</w:r></w:p>'
    )


def heading(value):
    return paragraph(value, bold=True, keep=True, before=160)


def page_break():
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'


def table(rows):
    widths = (560, 7850, 1150)
    grid = "".join(f'<w:gridCol w:w="{width}"/>' for width in widths)
    borders = "".join(
        f'<w:{edge} w:val="single" w:sz="4" w:color="9BAFBD"/>'
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV")
    )
    parts = [
        f'<w:tbl><w:tblPr><w:tblW w:w="{sum(widths)}" w:type="dxa"/>'
        f'<w:tblBorders>{borders}</w:tblBorders><w:tblLayout w:type="fixed"/></w:tblPr>'
        f'<w:tblGrid>{grid}</w:tblGrid>'
    ]
    for index, row in enumerate([("№", "Проверка", "Статус"), *rows]):
        header = "<w:tblHeader/>" if index == 0 else ""
        shading = '<w:shd w:fill="DCE7F1"/>' if index == 0 else ""
        parts.append(f"<w:tr><w:trPr><w:cantSplit/>{header}</w:trPr>")
        for column, (value, width) in enumerate(zip(row, widths)):
            text = paragraph(str(value), bold=index == 0, center=column != 1, size=22)
            parts.append(f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>{shading}</w:tcPr>{text}</w:tc>')
        parts.append("</w:tr>")
    return "".join(parts) + "</w:tbl>"


def jpeg_dimensions(image):
    offset = 2
    while offset + 9 < len(image) and image[offset] == 0xFF:
        marker = image[offset + 1]
        if marker in (0xC0, 0xC1, 0xC2):
            height = int.from_bytes(image[offset + 5:offset + 7], "big")
            width = int.from_bytes(image[offset + 7:offset + 9], "big")
            return width, height
        offset += 2 + int.from_bytes(image[offset + 2:offset + 4], "big")
    raise ValueError("Не удалось определить размер JPEG.")


def picture(index, caption, image):
    width, height = jpeg_dimensions(image)
    scale = min(5_700_000 / width, 3_350_000 / height)
    cx, cy = round(width * scale), round(height * scale)
    description = quoteattr(caption)
    return f'''
    <w:p><w:pPr><w:keepNext/><w:jc w:val="center"/></w:pPr><w:r><w:drawing>
      <wp:inline distT="0" distB="0" distL="0" distR="0">
        <wp:extent cx="{cx}" cy="{cy}"/>
        <wp:docPr id="{index}" name="Снимок {index}" descr={description}/>
        <a:graphic><a:graphicData uri="{PICTURE}">
          <pic:pic><pic:nvPicPr><pic:cNvPr id="{index}" name="Снимок {index}"/><pic:cNvPicPr/></pic:nvPicPr>
            <pic:blipFill><a:blip r:embed="rId{index}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>
            <pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>
              <a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>
          </pic:pic>
        </a:graphicData></a:graphic>
      </wp:inline>
    </w:drawing></w:r></w:p>'''


def write_docx(output: Path, total, counts, records, screenshots=None):
    summary = ", ".join(f"{status} — {number}" for status, number in sorted(counts.items()))
    stamp = datetime.now(ZoneInfo("Asia/Bishkek")).strftime("%d.%m.%Y, %H:%M")
    body = [
        paragraph("Практическая работа", bold=True, center=True, size=28, keep=True),
        paragraph("Тестирование пользователей в Django", bold=True, center=True, size=28, keep=True),
        heading("Цель работы"),
        paragraph("Добавить капчу на страницу входа и проверить регистрацию, вход и личный кабинет автоматическими тестами Django. Сохранить результаты запуска в Word."),
        heading("Результат выполнения"),
        paragraph(f"Выполнено тестов — {total}. Статусы — {summary or 'нет результатов'}. Дата и время запуска по Бишкеку — {stamp}."),
        paragraph("Django TestCase использует отдельную тестовую базу SQLite. После выполнения тестов база удаляется."),
        heading("Исходный пример и структура проекта"),
        paragraph("В папке django-test учебного репозитория показаны приложение users, тесты и пример формирования отчёта. В видео показаны регистрация через POST, переход на страницу входа и открытие личного кабинета. Для проекта «Ат Жол» задание выполнено в отдельной папке users-testing."),
        heading("Реализация регистрации, входа и личного кабинета"),
        paragraph("При регистрации форма проверяет уникальность имени, формат почты и совпадение паролей. Django сохраняет хеш пароля и переводит пользователя на страницу входа."),
        paragraph("На странице входа сервер выдаёт изображение с пятизначным кодом. Код действует пять минут, привязан к текущему сеансу и удаляется после первой попытки. При ошибке отображается новая капча. Пароль проверяется после капчи."),
        paragraph("Кабинет открывается после входа и показывает имя и почту текущего пользователя. При выходе Django завершает сеанс."),
        heading("Порядок повторного запуска"),
        paragraph("cd users-testing\npython manage.py migrate\npython manage.py test_users_report -v 2\npython manage.py runserver", font="Consolas", size=22),
        paragraph("Зависимости устанавливаются командой pip install -r requirements.txt. Отчёт сохраняется в reports/users-test-report.docx."),
        page_break(),
        heading("Результаты автоматических тестов"),
        paragraph("PASS означает, что все утверждения сценария прошли. Таблица сформирована по результатам текущего запуска Django."),
    ]
    ordered = []
    assigned = set()
    for group, label in GROUPS:
        matches = [record for record in records if f".{group}." in record[0]]
        if matches:
            ordered.append((label, matches))
            assigned.update(record[0] for record in matches)
    other = [record for record in records if record[0] not in assigned]
    if other:
        ordered.append(("Другие результаты", other))
    number = 0
    for label, tests in ordered:
        rows = []
        for _, description, status, _ in tests:
            number += 1
            rows.append((number, description, status))
        body.extend([heading(label), table(rows)])
    details = [record for record in records if record[3]]
    if details:
        body.extend([page_break(), heading("Подробности выполнения")])
        for name, _, status, detail in details:
            body.extend([heading(f"{name} — {status}"), paragraph(detail, size=20)])

    media = {}
    if screenshots is not None:
        body.extend([page_break(), heading("Скриншоты работы приложения")])
        body.append(paragraph("Снимки сделаны в браузере с HTML-страниц, полученных от Django Test Client."))
        for index, (filename, caption) in enumerate(SCREENSHOTS, 1):
            if index == 3:
                body.extend([page_break(), heading("Личный кабинет")])
            media[filename] = (screenshots / filename).read_bytes()
            body.extend([picture(index, caption, media[filename]), paragraph(f"Рисунок {index}. {caption}", center=True, size=22)])
    body.extend([
        heading("Использованные материалы"),
        paragraph("Учебный пример — https://github.com/narmuhamedov/TestingPO/tree/master/django-test"),
        paragraph("Видео «test users» — https://youtu.be/eUOtRNewDfY"),
        paragraph("Документация Django — https://docs.djangoproject.com/en/5.2/topics/testing/tools/"),
    ])
    body.append('<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1020" w:right="1020" w:bottom="1020" w:left="1247"/></w:sectPr>')
    document = (
        f'<w:document xmlns:w="{WORD}" xmlns:r="{OFFICE}" xmlns:wp="{WORD_DRAW}" '
        f'xmlns:a="{DRAW}" xmlns:pic="{PICTURE}"><w:body>{"".join(body)}</w:body></w:document>'
    )
    types = '''<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
      <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
      <Default Extension="xml" ContentType="application/xml"/>
      <Default Extension="jpg" ContentType="image/jpeg"/>
      <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
    </Types>'''
    relationships = "".join(
        f'<Relationship Id="rId{index}" Type="{OFFICE}/image" Target="media/{name}"/>'
        for index, name in enumerate(media, 1)
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", types)
        archive.writestr("_rels/.rels", f'<Relationships xmlns="{PACKAGE}"><Relationship Id="rId1" Type="{OFFICE}/officeDocument" Target="word/document.xml"/></Relationships>')
        archive.writestr("word/document.xml", document)
        archive.writestr("word/_rels/document.xml.rels", f'<Relationships xmlns="{PACKAGE}">{relationships}</Relationships>')
        for name, image in media.items():
            archive.writestr(f"word/media/{name}", image)
