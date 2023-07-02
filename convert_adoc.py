"""
Формат документов, полученный из Kramdoc, хотя и является полноценным Asciidoc форматом, но имеет ряд серьезных проблем, 
особенно для работы Antora, поэтому мы преобразуем все документы отдельно после прохода Kramdoc в этом скрипте. 
Эти процессы вынесены в отдельные скрипты, чтобы можно было легче отследить ошибки, возникающие на разных этапах.

В этом скрипте происходит дополнительная конвертация внутри файлов adoc под Antora.

Конвертация запускается для всех документов внутри указанных папок с сохранением структуры подпапок.
Папки указаны в НАСТРОЙКАХ в теле скрипта, стандартный набор: ['base', 'devdocs', 'manual', 'stdlib'] - 
это то, что получается в результате сборки документации в Julia.
Эти папки должны лежать внутри папки-источника (ее имя можно менять в НАСТРОЙКАХ, по умолчанию - converted_by_kramdoc).
Скрипт должен лежать рядом с папкой-источником.

Результат конвертации записывается в папку converted_by_adoc_converter (имя можно менять в НАСТРОЙКАХ) с сохранением разделения на подпапки. 
В процессе записывается подробный лог в отдельный файл с именем вида convert_adoc_2023-06-05_21-55-19.log

Основные преобразования данной конвертации подробно описаны на странице:
https://wiki.yandex.ru/engee/dokumentacija/razrabotka-dokumentacii/julia-dokumentacija/konvertacija-iz-md-v-adoc/

Какие преобразования производятся:
1) Удаляются лишние атрибуты из заголовка документа (doctype и тп.)
2) Удаляются лишние якоря разделов, расставленные Kramdoc
3) Главный заголовок страницы перемещается в самое начало документа (чтобы работала автоматическая подстановка названия документа)
4) В начале документа добавляется плашка "в процессе перевода", если документ не входит в список переведенных (список translated в теле скрипта) 
5) Преобразуются заголовки разделов docstrings
6) Преобразуются перекрестные ссылки 
7) Преобразуются блоки Admonition (Compat, Warning, Note, Tip) под формат Antora
8) Преобразуются блоки математических выражений под формат Antora 
9) Заменяются двойные дефисы на длинное тире не между пробелами (Antora автоматически делает это только между пробелами)
10) В некоторых случаях выставляется ширина столбцов таблиц (например, в документе base/punctuation.adoc)
11) ... Некоторые другие преобразования
"""

import os
import re
from distutils.dir_util import copy_tree
import logging
import sys
from datetime import datetime
import shutil

# НАСТРОЙКИ

# Задаем имя для папки с результатом конвертации
OUTPUT_FOLDER_NAME = 'converted_by_adoc_converter'
#OUTPUT_FOLDER_NAME = 'test_output'
# Задаем имена папок, в которых нужно провести конвертацию (плюс файлы из корня - index)
FOLDERS_TO_CONVERT = ['base', 'devdocs', 'manual', 'stdlib', 'index.adoc']
# Задаем папку-источник 
SOURCE_PATH = './converted_by_kramdoc'
#SOURCE_PATH = './test_input'
# Чистить ли папку для результата перед записью
CLEAN_TARGET_FOLDER = False


# Создаем файл лога в текущей папке
cur_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_file = os.path.join('./', 'convert_adoc_' + cur_time + '.log')

# Чистим файл лога, если он уже есть
if os.path.exists(log_file):
    os.remove(log_file)

# Настройки лога
logging.basicConfig(filename = log_file, #filemode='a', 
                    #format='%(asctime)s %(levelname)s %(message)s',
                    format='%(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.DEBUG)

# Выводим пути источника и результата 
logging.info('Source path: ' + str(os.path.abspath(SOURCE_PATH)))
logging.info('Output path: ' + str(os.path.abspath(OUTPUT_FOLDER_NAME)))


# Берем полные пути всех папок внутри SOURCE_PATH
subfolders = [f.path for f in os.scandir(SOURCE_PATH) if (f.is_dir() or str(f.path).endswith('.adoc'))]
# Берем имена всех папок
subfolders_names = [os.path.basename(f) for f in subfolders]

folders_found = False
# Проверяем имена папок внутри папки-источника
for folder in subfolders_names:
    if folder in FOLDERS_TO_CONVERT:
        #copy_tree(os.path.join(SOURCE_PATH, folder), os.path.join(output_path, folder))
        folders_found = True

# Если не нашли нужных папок, то выдаем сообщение и выходим
if not folders_found:
    logging.warning('No folders found in source folder with names from: ' + str(FOLDERS_TO_CONVERT))
    sys.exit()

# Если нашли, то начинаем конвертацию

# Создаем папку для результатов конвертации
#output_path = os.path.join(SOURCE_PATH, OUTPUT_FOLDER_NAME)
output_path = OUTPUT_FOLDER_NAME
if not os.path.exists(output_path):
    os.makedirs(output_path)

# Чистим ее, если она есть и настройка True
if os.path.exists(output_path) and CLEAN_TARGET_FOLDER:
    shutil.rmtree(output_path)

# Копируем папки с их поддеревьями в папку с результатами, проверяя имена папок
# Здесь же копируем файлы из корня (проверяя просто по расширению)
# Файл index.adoc переименовываем в _index.adoc (так как он не будет публиковаться сам по себе)
for folder in subfolders_names:
    if folder in FOLDERS_TO_CONVERT:
        if folder.endswith('.adoc'):
            if folder == 'index.adoc':
                shutil.copyfile(os.path.join(SOURCE_PATH, folder), os.path.join(output_path, '_index.adoc'))
            else:
                shutil.copyfile(os.path.join(SOURCE_PATH, folder), os.path.join(output_path, folder))
        else:
            copy_tree(os.path.join(SOURCE_PATH, folder), os.path.join(output_path, folder))

# Функция для вывода лога 
def log_it(message, count):
    if count > 0:
        logging.info('... ' + message + ': ' + str(count))

# Функция для парсинга блоков кода
# Возвращает список спанов (по номерам строк) всех блоков кода в документе
def find_code_lines(data):
    # Регулряка, возвращающая в группе 1 блоки кода
    #r = re.compile('\[,.{1,100}\]\n----\n(?P<group1>[\s\S]*?)----')
    r = re.compile('\n----\n(?P<group1>[\s\S]*?)----')
    
    # Записываем спаны по символам
    char_spans = []
    for m in r.finditer(data):
        char_spans.append(m.span(1))
    
    # Вычисляем спаны по строкам
    line_spans = []
    for span in char_spans:
        begin = data[:span[0]].count("\n")
        end = data[:span[1]].count("\n")
        line_spans.append((begin, end))
        
    return line_spans

# Функция проверяет, что данный индекс находится внутри одного из спанов
def in_spans(spans, line_index):
    res = False
    for span in spans:
        if line_index >= span[0] and line_index < span[1]:
            res = True
    return res


file_count = 0

# Задаем список переведенных документов. 
# От этого будет зависеть, добавлять ли в начале плашку "в процессе перевода".
translated = (
r'base\constants.adoc',
r'base\stacktraces.adoc',
r'base\arrays.adoc',
r'base\base.adoc',
r'base\c.adoc',
r'base\collections.adoc',
r'base\file.adoc',
r'base\io-network.adoc',
r'base\iterators.adoc',
r'base\libc.adoc',
r'base\math.adoc',
r'base\multi-threading.adoc',
r'base\numbers.adoc',
r'base\strings.adoc',
r'base\punctuation.adoc',
r'base\simd-types.adoc',
r'base\sort.adoc',
r'base\parallel.adoc',
r'manual\variables.adoc',
r'manual\arrays.adoc',
r'manual\command-line-options.adoc',
r'index.adoc',
r'manual\asynchronous-programming.adoc',
r'manual\documentation.adoc',
r'manual\embedding.adoc',
r'manual\environment-variables.adoc',
r'manual\faq.adoc',
r'manual\integers-and-floating-point-numbers.adoc',
r'manual\interfaces.adoc'
)

# Задаем список документов с docstrings, в которых нужно ограничить уровень глубины Contents до 1 (toclevel)
# Иначе в Contents показываются все блоки docstrings и это визуально перегружает дерево (см. RTFM-688)
toclevel_pages = (
r'base\arrays.adoc',
r'base\base.adoc',
r'base\collections.adoc',
r'base\io-network.adoc',
r'base\math.adoc',
r'base\multi-threading.adoc',
r'base\numbers.adoc',
r'base\sort.adoc',
r'base\parallel.adoc',
r'stdlib\LinearAlgebra.adoc',
r'stdlib\Dates.adoc',
r'stdlib\Logging.adoc',
r'stdlib\Random.adoc',
r'stdlib\REPL.adoc',
r'stdlib\SHA.adoc',
r'stdlib\Test.adoc'
)

# ВРЕМЕННО 
# Задаем списки заменяемых переводов для конкретных файлов (для случаев, где сборщик Julia выдавал ошибку)
# См. об этом https://wiki.yandex.ru/engee/dokumentacija/razrabotka-dokumentacii/julia-dokumentacija/spisok-oshibok-i-problem-pri-zagruzke-perevedennyx/

translation_io_network = {
'Take a raw file descriptor wrap it in a Julia-aware IO type, and take ownership of the fd handle. Call `open(Libc.dup(fd))` to avoid the ownership capture of the original handle.':
'Инкапсулировать необработанный дескриптор файла в тип ввода-вывода с поддержкой Julia и принять владение меткой-манипулятором файлового устройства. Вызвать `open(Libc.dup(fd))`, чтобы предотвратить передачу владения исходной меткой-манипулятором.',
'Do not call this on a handle that\'s already owned by some other part of the system.':
'Не вызывайте эту функцию для метки-манипулятора, которой уже владеет другая часть системы.',
'Run `command` asynchronously. Like `open(command, stdio; read, write)` except specifying the read and write flags via a mode string instead of keyword arguments. Possible mode strings are:':
'Запустить `command` в асинхронном режиме. Аналогично `open(command, stdio; read, write)`, за исключением того, что флаги чтения и записи задаются, используя строку режима вместо именованных аргументов. Возможны следующие строки режима:',
'Start running `command` asynchronously, and return a `process::IO` object.  If `read` is true, then reads from the process come from the process\'s standard output and `stdio` optionally specifies the process\'s standard input stream.  If `write` is true, then writes go to the process\'s standard input and `stdio` optionally specifies the process\'s standard output stream. The process\'s standard error stream is connected to the current global `stderr`.':
'Начать выполнение `command` в асинхронном режиме и вернуть объект `process::IO`.  Если `read` имеет значение true, считываемые данные процесса поступают из стандартного вывода процесса, и `stdio` дополнительно задается стандартный входной поток процесса.  Если `write` имеет значение true, записываемые данные отправляются в стандартный ввод процесса, и `stdio` дополнительно задается стандартный выходной поток процесса. Стандартный поток ошибок процесса подключается к текущему глобальному `stderr`.'
}
translation_c = {
'Copies a xref:stdlib/LinearAlgebra.adoc#LinearAlgebra.UniformScaling[`UniformScaling`] onto a matrix.':
'Копирует xref:stdlib/LinearAlgebra.adoc#LinearAlgebra.UniformScaling[`UniformScaling`] в матрицу.',
'In Julia 1.0 this method only supported a square destination matrix. Julia 1.1. added support for a rectangular matrix.':
'В Julia 1.0 этот метод поддерживал только квадратную матрицу назначения. В Julia 1.1. добавлена поддержка прямоугольной матрицы.'
}
translation_parallel = {
'Wait for a value to become available for the specified xref:stdlib/Distributed.adoc#Distributed.Future[`Future`].':
'Ожидает, когда станет доступным значение для указанного xref:stdlib/Distributed.adoc#Distributed.Future[`Future`].',
'Wait for a value to become available on the specified xref:stdlib/Distributed.adoc#Distributed.RemoteChannel[`RemoteChannel`].':
'Ожидает, когда станет доступным значение для указанного xref:stdlib/Distributed.adoc#Distributed.RemoteChannel[`RemoteChannel`].'
}

# В файле manual/documentation нужно сделать несколько конкретных замен для правильного отображения backticks
# и для замены ссылок, которые не заменились из-за начального пробела внутри списка (?)
# Делаем их по словарю

replace_documentation = {
'(```)':'(`+++`+++`)',
'(````)':'(`+++``+++`)',
'```α = 1```':'`+++``α = 1``+++`',
r'```\\alpha = 1```':r'`+++``\\alpha = 1``+++`',
'[`Int32`](../base/numbers.md#Core.Int32)':'xref:base/numbers.adoc#Core.Int32[`Int32`]',
'[`Int64`](../base/numbers.md#Core.Int64)':'xref:base/numbers.adoc#Core.Int64[`Int64`]'
}

# КОНВЕРТАЦИЯ

# Делаем все замены во всех файлах .adoc внутри output_path 
for paths, subdirs, files in os.walk(output_path):
    for file_name in files:
        full_path = os.path.join(paths, file_name)
        # Нормализуем путь к файлу (разные слэши бывают)
        norm_path = os.path.normpath(full_path)
        # Проверяем, что это файл adoc
        if norm_path.endswith('.adoc'):
            #print(norm_path)

            with open(norm_path, 'r', encoding='utf8') as file:
                #print(norm_path)
                data = file.read()
                logging.info('File: ' + str(norm_path))
                file_count += 1

                # Удаляем :doctype: book в заголовке страниц
                data_tuple = re.subn(r':doctype: book\n\n?', 
                                     r'', 
                                     data)
                data = data_tuple[0]
                log_it('Deleted :doctype: headers', data_tuple[1])

                # Удаляем :pp: {plus}{plus} в заголовке страниц
                data_tuple = re.subn(r':pp:\s{plus}{plus}\n\n?', 
                                     r'', 
                                     data)
                data = data_tuple[0]
                log_it('Deleted :pp: headers', data_tuple[1])

                # Удаляем :stem: latexmath в заголовке страниц
                data_tuple = re.subn(r':stem: latexmath\n\n?', 
                                     r'', 
                                     data)
                data = data_tuple[0]
                log_it('Deleted :stem: headers', data_tuple[1])

                # Удаляем лишние якоря с постфиксом "-1"
                data_tuple = re.subn(r'\+{3}.*?-1\">\+{6}</a>\+{3}\n\n?', 
                                     r'', 
                                     data)
                data = data_tuple[0]
                log_it('Deleted "-1" anchors', data_tuple[1])

                # Меняем местами якорь и главный заголовок
                data_tuple = re.subn(r'(?P<group1>\+{3}<a.*?a>\+{3})\n{1,3}(?P<group2>=\s.*)', 
                                     r'\2\n\n\1', 
                                     data)
                data = data_tuple[0]
                log_it('Main headers moved up', data_tuple[1])

                # Добавляем в начале документа плашку, если он еще не переведен
                if not norm_path.endswith(translated):
                    data_tuple = re.subn(r'(?P<group1>^=\s.*\n)', 
                                        r'\1\n[NOTE]\n====\nДокументация в процессе перевода.\n====\n', 
                                        data)
                    data = data_tuple[0]
                    log_it('Added header Translation in progress', data_tuple[1])

                # Заменяем заголовки разделов в docstrings
                data_tuple = re.subn(r'<<(?P<group1>.{1,200}),#>>\n\*', 
                                     r'[id="\1"]\n=== *', 
                                     data)
                data = data_tuple[0]
                log_it('Replaced docstring headers', data_tuple[1])

                # Убираем точки в заголовках разделов в docstrings
                data_tuple = re.subn(r'\&mdash;\s_(?P<group1>.{1,50}?)_\.', 
                                     r'— _\1_', 
                                     data)
                data = data_tuple[0]
                log_it('Deleted points in docstring headers', data_tuple[1])

                # Заменяем перекрестные ссылки в два этапа
                # Этап 1
                data_tuple = re.subn(r'link:(?P<group1>.{1,200}?).md', 
                                     r'xref:./\1.adoc', 
                                     data)
                data = data_tuple[0]
                log_it('Replaced links Part 1', data_tuple[1])

                # Этап 2
                data_tuple = re.subn(r'xref:./../', 
                                     r'xref:', 
                                     data)
                data = data_tuple[0]
                log_it('Replaced links Part 2', data_tuple[1])

                # Заменяем блоки Compat
                data_tuple = re.subn(r'!!! compat \"(?P<group1>.{1,100}?)\"\n\s{4}(?P<group2>.{1,10000}?)\n',
                                     r'[IMPORTANT]\n.Совместимость: \1\n====\n\2\n====\n', 
                                     data)
                data = data_tuple[0]
                log_it('Replaced Compat blocks', data_tuple[1])

                # Заменяем блоки Note
                data_tuple = re.subn(r'!!! note\n\s{4,5}(?P<group1>.{1,10000}?)\n',
                                     r'[NOTE]\n====\n\1\n====\n', 
                                     data)
                data = data_tuple[0]
                log_it('Replaced Note blocks', data_tuple[1])

                # Заменяем блоки Warning
                data_tuple = re.subn(r'!!! warning\n\s{4,5}(?P<group1>.{1,10000}?)\n',
                                     r'[WARNING]\n====\n\1\n====\n', 
                                     data)
                data = data_tuple[0]
                log_it('Replaced Warning blocks', data_tuple[1])

                # Заменяем блоки Tip
                data_tuple = re.subn(r'!!! tip\n\s{4,5}(?P<group1>.{1,10000}?)\n',
                                     r'[TIP]\n====\n\1\n====\n', 
                                     data)
                data = data_tuple[0]
                log_it('Replaced Tip blocks', data_tuple[1])

                # Заменяем блоки sidebar (см. RTFM-682)
                data_tuple = re.subn(r'!!! sidebar \"(?P<group1>.{1,1000}?)\"\n\s{4}(?P<group2>.{1,10000}?)\n',
                                     r'[NOTE]\n.\1\n====\n\2\n====\n', 
                                     data)
                data = data_tuple[0]
                log_it('Replaced sidebar blocks', data_tuple[1])
                
                # Присоединяем к блокам Note, Warning, Tip строки в четверных точках
                data_tuple = re.subn(r'====\n\+?\n\.{4}\n(?P<group1>[\s\S]{1,10000}?)\.{4}',
                                     r'\n\1\n====\n', 
                                     data)
                data = data_tuple[0]
                log_it('Added parts in four points to admonition blocks', data_tuple[1])

                # Вставляем дополнительные переносы строки для списков внутри блоков Admonition (см. RTFM-682)
                if not norm_path.endswith('Markdown.adoc'):
                    data_tuple = re.subn(r'\n[^\S\r\n]{2}\*[^\S\r\n]',
                                        r'\n\n  * ', 
                                        data)
                    data = data_tuple[0]
                    log_it('Added extra line breaks in lists', data_tuple[1])

                # Заменяем блоки математических выражений
                # Все что между двух $ но слева обязательно пробел! Иначе много лишних захватов
                # Пробел, но не newline можно записать только так: [^\S\r\n]
                """
                data_tuple = re.subn(r'[^\S\r\n]\$(?P<group1>[^\$`\r\n]{1,100}?)\$',
                                     r' stem:[\1]', 
                                     data)
                data = data_tuple[0]
                log_it('Replaced Math blocks', data_tuple[1])
                """
                # Теперь делаем через цикл, чтобы не заменять в блоках с кодом
                # Парсим текст на блоки кода
                code_lines = find_code_lines(data)
                #print(code_lines)
                
                lines_edited = []
                data_lines = data.splitlines()
                replace_count = 0
                for i in range(len(data_lines)):
                    if in_spans(code_lines, i):
                        lines_edited.append(data_lines[i])
                        #print('line in spans:', i)
                    else:
                        data_tuple = re.subn(r'[^\S\r\n]\$(?P<group1>[^\$`\r\n]{1,100}?)\$',
                                            r' stem:[\1]', 
                                            data_lines[i])
                        if data_tuple[1] == 0:
                            lines_edited.append(data_lines[i])
                        else:
                            lines_edited.append(data_tuple[0])
                            replace_count += data_tuple[1]
                # Добавляем пустую строку в конце, потому что она там была везде
                lines_edited.append('')
                data = '\n'.join(lines_edited)
                log_it('Replaced Math blocks', replace_count)

                # Добавляем ограничение на уровни в Contents (см. RTFM-688)
                if norm_path.endswith(toclevel_pages):
                    data_tuple = re.subn(r'^(?P<group1>=\s[^\s].*?\n)', 
                                        r'\1:page-toclevels: 1\n', 
                                        data)
                    data = data_tuple[0]
                    log_it('Added page-toclevels', data_tuple[1])

                # Заменяем якоря с одинарными кавычками внутри (Kramdoc с таким не справляется)
                data_tuple = re.subn(r'<a id=\'(?P<group1>.{1,1000}\'.{1,1000}?)\'></a>',
                                     r'+++<a id="\1">++++++</a>+++', 
                                     data)
                data = data_tuple[0]
                log_it('Replaced id with single quote', data_tuple[1])

                # Обрамляем __текст__ в двойных подчеркиваниях в +++ (см. RTFM-536)
                # Сначала только внутри backticks: `__FILE__` -> `+++__FILE__+++`
                # Слева и справа может быть дополнительный текст
                data_tuple = re.subn(r'(?P<group1>`\S{0,100}?)(?P<group2>__\S{1,100}__)(?P<group3>\S{0,100}?`)',
                                     r'\1+++\2+++\3', 
                                     data)
                data = data_tuple[0]
                log_it('Adding "+++" to text in backticks', data_tuple[1])

                # Обрамляем __текст__ в двойных подчеркиваниях в +++ (см. RTFM-536)
                # Теперь только в ссылках: xref:./base.adoc#Base.@__FILE__ -> xref:./base.adoc#Base.@+++__FILE__+++
                # Ссылки обрабатываются раньше. Порядок замен важен!
                data_tuple = re.subn(r'(?P<group1>xref:\S{1,100}?)(?P<group2>__\S{1,100}?__)',
                                     r'\1+++\2+++', 
                                     data)
                data = data_tuple[0]
                log_it('Adding "+++" to text in xref links', data_tuple[1])

                # Заменяем двойные дефисы на длинное тире после кода неразрывного пробела 
                # (Antora делает это только между двух обычных пробелов)
                replace_count = data.count('&nbsp;-- ')
                data = data.replace('&nbsp;-- ',
                                    '&nbsp;— ')
                log_it("Replaced two hyphens", replace_count)

                # Заменяем отбитые закрывающие квадратные скобки \] на неотбитые ]
                # Kramdoc отбивает такие скобки в некоторых контекстах, например в сносках (footnote), из-за чего они ломаются
                # Но в ссылках (xref) эти отбивания нужны, поэтому делаем negative lookahead на сочетание )` - в ссылках только в таком контексте это встречается
                # Это не очень честно, но по-честному нужно парсить весь текст на фрагменты внутри ссылок и внутри сносок, а это все сильно усложнит.
                # (см. RTFM-687)
                data_tuple = re.subn(r'\\](?!\)`)',
                                     r']', 
                                     data)
                data = data_tuple[0]
                log_it("Replaced escaped closing square brackets '\]'", data_tuple[1])

                # Заменяем ссылки (внешние на http) формата Markdown на формат Asciidoc (см. RTFM-672)
                # В некоторых блоках Kramdoc сам их не заменяет, приходится доделывать. Файл Markdown не трогаем, так как там есть такой пример на Markdown
                if not norm_path.endswith('Markdown.adoc'):
                    data_tuple = re.subn(r'\[(?P<group1>[^\n\r]{1,10000}?)\]\((?P<group2>http[^\n\r]{1,10000}?)\)',
                                        r'\2[\1]', 
                                        data)
                    data = data_tuple[0]
                    log_it('Replaced links from .md to .adoc', data_tuple[1])

                # На странице Punctuation делаем специальные преобразования 
                if norm_path.endswith('base\punctuation.adoc'):
                    # Задаем относительную ширину столбцов таблицы  
                    data_tuple = re.subn(r'\|===\n\|',
                                        r'[cols="10%,90%"]\n|===\n|', 
                                        data)
                    data = data_tuple[0]
                    log_it('Table columns width', data_tuple[1])

                    # Убираем одно лишнее экранирование знака | (или)
                    replace_count = data.count('\\\\|')
                    data = data.replace('\\\\|', r'\|')
                    log_it("Replaced OR '\\|'", replace_count)

                    # Экранируем тильду
                    replace_count = data.count('`~`')
                    data = data.replace('`~`', r'`+~+`')
                    log_it("Replaced tilde", replace_count)

                    # Экранируем backticks
                    replace_count = data.count('`` ``')
                    data = data.replace('`` ``', r'`+++` `+++`')
                    log_it("Escaped backticks ` `", replace_count)
                
                # На странице _index.adoc удаляем весь текст из шапки, оставляем только после слова "Введение"
                if norm_path.endswith('_index.adoc'):  
                    data_tuple = re.subn(r'[\s\S]*= Введение(?P<group1>[\s\S]*)',
                                        r'\1', 
                                        data)
                    data = data_tuple[0]
                    log_it('Deleted header in index', data_tuple[1])

                # Замены конкретных последовательностей, ломающих форматирование adoc (символы '=' мешаются)
                # В manual/strings.adoc
                replace_count = data.count('(str, i, n=1)')
                data = data.replace('(str, i, n=1)',
                                    '+++(str, i, n=1)+++')
                log_it("Replaced '(str, i, n=1)'", replace_count)

                # В manual/arrays.adoc
                replace_count = data.count('similar(A,T=eltype(A),dims=size(A))')
                data = data.replace('similar(A,T=eltype(A),dims=size(A))',
                                    '+similar(A,T=eltype(A),dims=size(A))+')
                log_it("Replaced 'similar(A,T=eltype(A),dims=size(A))'", replace_count)

                # В manual/faq.adoc
                replace_count = data.count('`#=`')
                data = data.replace('`#=`', '`+#=+`')
                log_it("Replaced '`#=`'", replace_count)

                replace_count = data.count('`=#`')
                data = data.replace('`=#`', '`+=#+`')
                log_it("Replaced '`=#`'", replace_count)

                # В manual/calling-c-and-fortran-code.adoc
                replace_count = data.count('dims, own = false')
                data = data.replace('dims, own = false', 'dims, own +++=+++ false')
                log_it("Replaced 'dims, own = false'", replace_count)

                # ВРЕМЕННО 
                # Добавляем прямо здесь переводы объектов, которые не собираются в julia из-за ошибок
                if norm_path.endswith('base\io-network.adoc'):
                    replace_count = 0
                    for item in translation_io_network:
                        source = item
                        target = translation_io_network[item]
                        replace_count += data.count(source)
                        data = data.replace(source, target)
                    log_it("Replaced translated sentences", replace_count)
                if norm_path.endswith('base\c.adoc'):
                    replace_count = 0
                    for item in translation_c:
                        source = item
                        target = translation_c[item]
                        replace_count += data.count(source)
                        data = data.replace(source, target)
                    log_it("Replaced translated sentences", replace_count)
                if norm_path.endswith('base\parallel.adoc'):
                    replace_count = 0
                    for item in translation_parallel:
                        source = item
                        target = translation_parallel[item]
                        replace_count += data.count(source)
                        data = data.replace(source, target)
                    log_it("Replaced translated sentences", replace_count)
                
                # Замены по словарю в manual/documentation
                if norm_path.endswith('manual\documentation.adoc'):
                    replace_count = 0
                    for item in replace_documentation:
                        source = item
                        target = replace_documentation[item]
                        replace_count += data.count(source)
                        data = data.replace(source, target)
                    log_it("Replaced with dict replace_documentation", replace_count)

                    # В этом же документе нужно убрать все одиночные пробелы в начале строк.
                    # Они там остаются от длинного списка, но в блоках Admonition они мешаются.
                    data_tuple = re.subn(r'\n[^\S\r\n](?=[^\s])',
                                         r'\n', 
                                        data)
                    data = data_tuple[0]
                    log_it('Deleted single spaces', data_tuple[1])

            # Записываем текст после всех замен обратно в файл
            with open(norm_path, 'w', encoding='utf8') as file:
                file.write(data)

# Выводим количество сконвертированных файлов
logging.info('Files converted total: ' + str(file_count))

# Выводим в командную строку сообщение об окончании процесса
print('Files converted total: ' + str(file_count))
print('Conversion finished')



