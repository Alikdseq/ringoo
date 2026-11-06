# -*- coding: utf-8 -*-
"""Generate Word report: Ringo integrations (1C, Sber, kassa)."""

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


def set_run_font(run, name="Times New Roman", size=12, bold=False, color=None):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.bold = bold
    if color is not None:
        run.font.color.rgb = color


def main() -> None:
    out = Path(__file__).resolve().parents[1] / "docs" / "Отчёт_интеграции_Ringo_1С_Сбер_касса.docx"
    doc = Document()

    for section in doc.sections:
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2)

    def add_heading_custom(text, level=1):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(16 if level == 1 else 12)
        p.paragraph_format.space_after = Pt(8)
        p.paragraph_format.line_spacing = 1.15
        run = p.add_run(text)
        sizes = {1: 16, 2: 13, 3: 12}
        set_run_font(run, size=sizes.get(level, 12), bold=True, color=RGBColor(0x1A, 0x1A, 0x1A))
        return p

    def add_body(text, first_line_indent=False):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(8)
        p.paragraph_format.line_spacing = 1.2
        if first_line_indent:
            p.paragraph_format.first_line_indent = Cm(1.25)
        run = p.add_run(text)
        set_run_font(run, size=12)
        return p

    def add_bullet(text, numbered=False, number=None):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.2
        p.paragraph_format.left_indent = Cm(0.75)
        prefix = f"{number}. " if numbered else "• "
        run = p.add_run(prefix + text)
        set_run_font(run, size=12)
        return p

    # Title
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(6)
    set_run_font(title.add_run("Отчёт по интеграции сайта Ringo"), size=18, bold=True)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.paragraph_format.space_after = Pt(4)
    set_run_font(
        subtitle.add_run("1С, онлайн-оплата Сбербанк и онлайн-касса"),
        size=14,
        bold=True,
    )

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.paragraph_format.space_after = Pt(18)
    set_run_font(
        meta.add_run("Статус работ и следующие шаги"),
        size=11,
        color=RGBColor(0x55, 0x55, 0x55),
    )

    add_body(
        "Ниже приведено краткое описание проделанной работы по интеграциям, "
        "полученной информации от специалистов и того, что осталось до полноценного запуска.",
        first_line_indent=True,
    )

    # 1. 1C
    add_heading_custom("1. Интеграция с 1С", level=1)
    add_body(
        "Я связался со специалистом по 1С Аланом и получил информацию о том, "
        "как сайт может взаимодействовать с системой учёта.",
        first_line_indent=True,
    )

    add_heading_custom("Что предоставлено специалистом", level=2)
    for i, t in enumerate(
        [
            "Адрес тестовой базы 1С и способ подключения к ней.",
            "Способ получения списка категорий товаров.",
            "Способ получения товаров, их цен и остатков.",
            "Способ регистрации покупателя в 1С и получения его идентификатора.",
        ],
        1,
    ):
        add_bullet(t, numbered=True, number=i)

    add_body(
        "На основании этой информации на стороне сайта подготовлена основа для обмена данными с 1С: "
        "получение информации о товарах и категориях, обработка полученных данных и механизм "
        "регистрации покупателя.",
        first_line_indent=True,
    )

    add_heading_custom("Что ещё нужно сделать", level=2)
    add_body(
        "От Алана необходимо получить техническую инструкцию по передаче оформленных заказов "
        "с сайта в 1С. Нужно понимать:",
        first_line_indent=True,
    )
    for i, t in enumerate(
        [
            "какие данные передавать;",
            "каким способом создавать заказ;",
            "как проверять результат;",
            "как избежать появления дубликатов.",
        ],
        1,
    ):
        add_bullet(t, numbered=True, number=i)

    add_body(
        "После получения этой информации можно реализовать передачу заказов и проверить, "
        "что они корректно появляются в 1С.",
        first_line_indent=True,
    )
    add_body(
        "Также необходимо проверить обмен непосредственно с тестовой базой: пока основная часть "
        "автоматических проверок выполнялась без подключения к реальной системе.",
        first_line_indent=True,
    )

    # 2. Sber
    add_heading_custom("2. Интеграция онлайн-оплаты через Сбербанк", level=1)
    add_body(
        "По онлайн-оплате изучена документация Сбербанка и подготовлен механизм подключения "
        "платёжной системы к сайту.",
        first_line_indent=True,
    )

    add_heading_custom("Что уже сделано", level=2)
    for i, t in enumerate(
        [
            "Подготовлен механизм создания платежа при оформлении заказа.",
            "Реализован переход покупателя на страницу оплаты Сбербанка.",
            "Подготовлена проверка результата оплаты и обновление статуса заказа на сайте.",
            "Добавлена обработка уведомлений от банка, чтобы заказ корректно обновлялся после оплаты.",
            "Предусмотрена обработка неоплаченных и просроченных заказов, а также повторных уведомлений от банка.",
            "Добавлены проверки и автоматические тесты для основных сценариев.",
        ],
        1,
    ):
        add_bullet(t, numbered=True, number=i)

    add_body(
        "Последняя проверка прошла успешно: 28 автоматических тестов. Они выполнялись в тестовом режиме, "
        "без проведения реального платежа через Сбербанк.",
        first_line_indent=True,
    )

    add_heading_custom("Что получено от Сбербанка", level=2)
    add_body(
        "Получена информация о порядке подключения интернет-эквайринга, документация по API "
        "и адрес тестового контура:",
        first_line_indent=True,
    )
    link = doc.add_paragraph()
    link.paragraph_format.space_after = Pt(8)
    link.paragraph_format.left_indent = Cm(0.75)
    set_run_font(
        link.add_run("https://ecomtest.sberbank.ru/doc"),
        size=12,
        color=RGBColor(0x0B, 0x57, 0xD0),
    )

    add_body(
        "Для проверки необходимо получить тестовые логин и пароль, после чего можно проводить "
        "платежи тестовыми картами.",
        first_line_indent=True,
    )

    add_heading_custom("Что осталось", level=2)
    for i, t in enumerate(
        [
            "Получить тестовые доступы от Сбербанка.",
            "Развернуть изменения на тестовом сервере и настроить адреса, по которым банк будет отправлять уведомления о результатах оплаты.",
            "Провести реальные тестовые платежи и проверить успешную оплату, отказ, отмену и обновление статуса заказа.",
            "После успешного тестирования перейти к подключению боевых доступов и запуску реальных платежей.",
        ],
        1,
    ):
        add_bullet(t, numbered=True, number=i)

    add_body("Боевые платежи пока не включены.", first_line_indent=True)

    # 3. Kassa
    add_heading_custom("3. Онлайн-касса и чеки", level=1)
    add_body(
        "Отдельно необходимо решить вопрос формирования кассовых чеков при онлайн-оплате.",
        first_line_indent=True,
    )
    add_body(
        "Нужно согласовать, будет ли чек формироваться через Сбербанк или через отдельный сервис "
        "онлайн-кассы.",
        first_line_indent=True,
    )
    add_body(
        "После выбора схемы необходимо получить соответствующие доступы и настройки, подготовить "
        "передачу данных о товарах и оплате, а затем проверить формирование чеков.",
        first_line_indent=True,
    )
    add_body(
        "Этот этап пока не завершён: требуется согласовать способ подключения и получить "
        "необходимые данные от ответственных специалистов.",
        first_line_indent=True,
    )

    # 4. Next steps
    add_heading_custom("4. Что необходимо для завершения работ", level=1)
    add_body(
        "Основная техническая подготовка механизма онлайн-оплаты выполнена. По 1С подготовлена "
        "часть обмена данными.",
        first_line_indent=True,
    )
    add_body(
        "Чтобы довести всё до полноценной работы, необходимо:",
        first_line_indent=True,
    )

    steps = [
        ("Сбербанк", "получить тестовые доступы и проверить оплату на тестовом сервере."),
        (
            "Алан / 1С",
            "получить инструкцию по созданию заказов в 1С и реализовать передачу заказов с сайта.",
        ),
        ("Онлайн-касса", "выбрать способ формирования чеков и получить необходимые доступы."),
        (
            "Тестирование",
            "проверить полный процесс: оформление заказа на сайте, оплату, передачу заказа в 1С и формирование чека.",
        ),
        (
            "Запуск",
            "после успешных проверок подключить рабочие доступы и запустить интеграции в production.",
        ),
    ]
    for i, (who, what) in enumerate(steps, 1):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.2
        p.paragraph_format.left_indent = Cm(0.75)
        set_run_font(p.add_run(f"{i}. {who}: "), size=12, bold=True)
        set_run_font(p.add_run(what), size=12)

    add_body(
        "Параллельно сайт готовится к тестированию, чтобы после получения всех необходимых доступов "
        "можно было перейти к проверкам без лишних задержек.",
        first_line_indent=True,
    )

    # Summary
    add_heading_custom("Итог", level=1)
    add_body(
        "Работа по интеграциям уже ведётся. Часть механизмов реализована и проверена автоматическими "
        "тестами. Основные оставшиеся вопросы связаны с получением доступов, согласованием передачи "
        "заказов с 1С и выбором схемы онлайн-кассы. После этого можно будет завершить подключение "
        "и проверить весь процесс в реальной работе.",
        first_line_indent=True,
    )

    add_heading_custom("Сводка по статусу", level=1)
    table = doc.add_table(rows=4, cols=3)
    table.style = "Table Grid"
    headers = ["Направление", "Статус", "Блокер"]
    rows = [
        [
            "1С (каталог и партнёры)",
            "Частично готово",
            "Инструкция по созданию заказов, живой тест базы",
        ],
        [
            "Сбербанк (оплата)",
            "Код готов, тест без шлюза",
            "Тестовые логин и пароль, staging и callback",
        ],
        ["Онлайн-касса", "Не начато", "Выбор схемы и доступы"],
    ]
    for j, h in enumerate(headers):
        cell = table.rows[0].cells[j]
        cell.text = ""
        set_run_font(cell.paragraphs[0].add_run(h), size=11, bold=True)
    for i, row in enumerate(rows, 1):
        for j, val in enumerate(row):
            cell = table.rows[i].cells[j]
            cell.text = ""
            set_run_font(cell.paragraphs[0].add_run(val), size=11)

    doc.add_paragraph()
    footer = doc.add_paragraph()
    set_run_font(
        footer.add_run("Документ подготовлен для передачи заказчику. Боевые платежи не включены."),
        size=10,
        color=RGBColor(0x66, 0x66, 0x66),
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out))
    print(out.resolve())


if __name__ == "__main__":
    main()
