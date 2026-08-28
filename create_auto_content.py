"""
Скрипт генерации авто-контента.

Здесь генерируются:
- Алфавитный указатель https://tengri.postgrespro.ru/documentation/ru/stable/glossary
- Списки функций для страницы https://tengri.postgrespro.ru/documentation/ru/stable/functions/
- Файл с докстрингами функций (для будущей встройки в интерфейс)
- Файл с тестовыми запросами SQL из всех примеров в документации
- Файл с описаниями объектов для вставки в промпты AI-агентов

Здесь же предварительно копируются общие файлы для сборок на разных языках из documentation-shared

Запускаем из корня репозитория.
"""
import os
import re
import yaml
import json
import shutil

# Настраиваем логирование
'''
from loguru import logger
logger.remove()
logger.add(
    sys.stderr,
    #format="{time:HH:mm:ss} | <yellow>{level}</yellow> | {message}"
    format =
    #"<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level>| "
    #"<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)
'''


# НАСТРОЙКИ ПУТЕЙ

# Путь к исходникам документации
DOCUMENTATION_FOLDER = 'documentation-ru'
# Локали
LOCALES = ['ru', 'en']
# Выводить ли подробный лог
LOG_ON = False

FUNCTION_FOLDER = {}
MANUAL_FOLDER = {}
QUERY_FOLDER = {}
ADOC_DICT_FILE = {}
PARTIALS_FUNC_LISTS = {}
INDEX_OUTPUT = {}
JSON_DOCSTRINGS = {}

for locale in LOCALES:
    root = DOCUMENTATION_FOLDER.replace('-ru', f'-{locale}')
    # Путь к страницам функций
    FUNCTION_FOLDER[locale] = os.path.join(root, 'modules', 'ROOT', 'pages', 'functions')
    # Путь до manual
    MANUAL_FOLDER[locale] = os.path.join(root, 'modules', 'ROOT', 'pages', 'manual')
    # Путь до запросов
    QUERY_FOLDER[locale] = os.path.join(root, 'modules', 'ROOT', 'pages', 'sql_queries')
    # Словарь adoc
    ADOC_DICT_FILE[locale] = os.path.join(root, 'modules', 'ROOT', 'partials', 'dict.adoc')
    # Путь куда складываем сгенерированные файлы со списками функций
    PARTIALS_FUNC_LISTS[locale] = os.path.join(root, 'modules', 'ROOT', 'partials', 'function_lists')
    # Создаем эти папки, так как они в gitignore
    os.makedirs(PARTIALS_FUNC_LISTS[locale], exist_ok=True)

    # Сгенерированный файл с указателем
    INDEX_OUTPUT[locale] = os.path.join(root, 'modules', 'ROOT', 'partials', 'objects_index.adoc')
    
    # Сгенерированный файл с докстрингами в json
    os.makedirs('build_docstrings', exist_ok=True)
    JSON_DOCSTRINGS[locale] = os.path.join('build_docstrings', f'docstrings-{locale}.json')

# Файл для текстов примеров запросов для тестов
JSON_QUERIES = os.path.join('build_docstrings', 'queries_from_docs.json')

# Файл для описаний функций для AI-агентов
FUNCTIONS_FOR_AI_FILE = os.path.join('build_docstrings', 'object_descriptions_for_ai.md')

# Файл с ручной разметкой для разных объектов
OBJECTS_MARKUP = os.path.join('auto_content', 'objects.yml')


# Копируем файлы общие для локалей 
# (потом можно будет сделать через symlinks, но это сложно из-за подпапок)
for locale in LOCALES:
    doc_root = DOCUMENTATION_FOLDER.replace('-ru', f'-{locale}')
    shutil.copytree('documentation-shared', doc_root, dirs_exist_ok=True)

'''
SYMLINK_PATHS = [
(os.path.join(DOC_SHARED, 'images'), os.path.join('modules', 'ROOT', 'images')),
(os.path.join(DOC_SHARED, 'nav-tree.adoc'), os.path.join('modules', 'ROOT', 'partials', 'nav-tree.adoc'))
]
# Делаем symlinks 
for locale in LOCALES:
    doc_root = DOCUMENTATION_FOLDER.replace('-ru', f'-{locale}')
    for pair in SYMLINK_PATHS:
        os.symlink(pair[0], pair[1], target_is_directory=True)
'''

# Проверяем, что стоим в нужном месте. Если нет, выходим
if not os.path.isdir(DOCUMENTATION_FOLDER):
    print(f'Folder "{DOCUMENTATION_FOLDER}" not found in current path. Exiting.')
    quit()

# Регулярка для парсинга страниц функций
#function_regex = re.compile(r'\n\[id=(?P<name>.+?)\]\n==[\S\s]*?\nОписание:: (?P<description>[\S\s]*?)\nИспользование::')
function_regex = {
'ru': re.compile(r'\n== (Оператор )?`(?P<name>.+?)`\n[\S\s]*?\nОписание:: (?P<description>[\S\s]*?)\nИспользование:: (?P<usage>.*?)\n'),
'en': re.compile(r'\n== (Operator )?`(?P<name>.+?)`\n[\S\s]*?\Description:: (?P<description>[\S\s]*?)\nUsage:: (?P<usage>.*?)\n')
}

# Регулярка для парсинга страниц с командами
commands_regex = re.compile(r'\n\*\s<<.*?,\s?`(?P<name>.+?)`>>\s--\s\{(?P<dict>.+?)\}')

# Регулярка для парсинга словаря adoc
adoc_dict_regex = re.compile(r'(?<=\n):(?P<key>.+?): (?P<value>.+)\n')

# Регулярка для парсинга текстов запросов (для тестов)
queries_regex = re.compile(r'\n\[source,sql\]\n----\n(?P<query>[\S\s]*?)----\n')

# Словарь для сохранения текстов запросов
queries_dict = {}

# Описания функций и типов для AI-агентов
functions_for_ai = {}
functions_for_ai['types'] = '## DATA TYPES DESCRIPTIONS FOR SQL QUERIES\n'
functions_for_ai['functions'] = '\n## FUNCTIONS DESCRIPTIONS FOR SQL QUERIES\n'

# Список операторов (у них различается имя и id)
operators = {
'+':'plus_operator',
'-':'minus_operator',
'||':'concat_operator',
'*':'multiplication_operator',
'/':'float_division_operator',
'%':'remainder_operator',
'^':'exponent_operator',
'~':'tilda_operator',
'::':'double_colon_operator',
'<':'less_than_operator',
'>':'greater_than_operator',
r'\<=':'less_than_or_equal_to_operator',
'>=':'greater_than_or_equal_to_operator',
'=':'equal_operator',
'<>':'not_equal_operator',
'BETWEEN':'between_operator'
}

types_dict = {
'ru':
    {
    'function': 'Функция',
    'operator': 'Оператор',
    'command': 'Выражение {SQL}',
    'data type': 'Тип данных',
    'query': 'Выражение {SQL}',
    'python_function':'Функция {Python}'
    },
'en':
    {
    'function': 'Function',
    'operator': 'Operator',
    'command': '{SQL} expression',
    'data type': 'Data type',
    'query': '{SQL} expression',
    'python_function':'{Python} function'
    },
}

category_dict = {
'ru':
    {
    'query_default_desc':'Элемент запроса `SELECT`',
    'select_desc':'Запрос `SELECT`',
    'explain_desc':'Вывод плана запроса `SELECT`',
    'func_alias':'Псевдоним функции',
    'type_alias':'Псевдоним типа данных',
    'oper_alias':'Псевдоним оператора'
    },
'en':
    {
    'query_default_desc':'`SELECT` query element',
    'select_desc':'`SELECT` query',
    'explain_desc':'Output `SELECT` query plan',
    'func_alias':'Alias for function',
    'type_alias':'Alias for data type',
    'oper_alias':'Alias for operator'
    }
}

mes_dict = {
'ru':
    {
    'objects_total':'Всего объектов'
    },
'en':
    {
    'objects_total':'Objects total'
    }
}

# Загружаем ручную разметку
objects_markup_dict = {}
try:
    with open(OBJECTS_MARKUP, "rb") as file:
        try:
            objects_markup_dict = yaml.safe_load(file)
            print(f'Length of loaded list from "{OBJECTS_MARKUP}": {len(objects_markup_dict)}')
        except:
            print(f'Not valid yaml file: "{OBJECTS_MARKUP}"')
except FileNotFoundError:
    print(f'File "{OBJECTS_MARKUP}" not found')
except:
    print(f'Something wrong with {OBJECTS_MARKUP}')

#print(objects_markup_dict)

# Для учета функций из DuckDB
func_names = []


# Начинаем генерацию (по локалям)

for locale in LOCALES:
    print(f'Starting creating auto content for locale: {locale}')
    # Загружаем словарь adoc 
    adoc_dict = {}
    try:
        with open(ADOC_DICT_FILE[locale], 'r', encoding='utf8') as file:
            file_text = file.read()
    except FileNotFoundError:
        print(f'File "{ADOC_DICT_FILE[locale]}" not found')
        file_text = ''
    except:
        print(f'Something wrong with {ADOC_DICT_FILE[locale]}')
        file_text = ''

    # Накладываем регулярку
    adoc_dict_groups = [m.groupdict() for m in adoc_dict_regex.finditer(file_text)]
    # Записываем в словарь
    for adoc_d in adoc_dict_groups:
        adoc_dict[adoc_d['key']] = adoc_d['value']


    """
    Словарь объектов для результатов

    Структура:

    {'<имя объекта> <тип объекта>':
    [<имя объекта> без backticks, <тип объекта>, <категория>, <описание>, <ссылка>, <использование>]}

    Составной ключ - для сквозной алфавитной сортировки.
    """
    objects = {}

    # Категории для функций. Собираем из имен файлов в папке functions.
    func_categories = []

    # Собираем объекты из functions
    for paths, subdirs, files in os.walk(FUNCTION_FOLDER[locale]):
        for file_name in files:

            # Полный путь текущего файла
            full_path = os.path.join(paths, file_name)
            # Имя текущей папки
            cur_folder = os.path.basename(os.path.dirname(full_path))
            
            if file_name == 'index.adoc':
                continue
            if not file_name.endswith('.adoc'):
                continue
            
            file_name_short = file_name.replace('.adoc', '')
            func_categories.append(file_name_short)

            with open(full_path, 'r', encoding='utf8') as file:
                file_text = file.read()
            
            # Накладываем регулярку
            func_groups = [m.groupdict() for m in function_regex[locale].finditer(file_text)]

            for func in func_groups:
                #print(func)
                func_name = f'{func["name"].replace("()", "")}'
                # Случай операторов
                if func["name"] in operators.keys():
                    #func_name = f'Оператор `{func["name"]}`'
                    link_name = operators[func["name"]]
                    #sort_name = {func["name"]}
                    sort_name = func["name"]
                    type = 'operator'
                # Случай обычных функций
                else:
                    #func_name = f'`{func["name"].replace('()', '')}`'
                    sort_name = func["name"].replace('()', '')
                    # Для функций Питон свой тип и своя логика ссылок
                    if file_name == 'tengri_functions.adoc':
                        link_name = func["name"].replace('()', '').replace('tengri.', '')
                        type = 'python_function'
                    else:
                        link_name = func["name"].replace('()', '')
                        type = 'function'
                
                # Достаем usage 
                if 'usage' in func.keys():
                    usage = func["usage"]
                else:
                    usage = ''

                link = f'xref:ROOT:functions/{file_name}#{link_name}'
                objects[f'{sort_name} {type}'] = [func_name, type, file_name_short, func["description"], link, usage]
                if locale == 'ru':
                    func_names.append(func_name)
    #print(func_categories)
    #print(objects)
    #for k,v in objects.items():
    #    print(k,v)
    #    print()


    # Генерим файлы со списками функций для страницы раздела функций
    for cat in func_categories:
        output_file_name = os.path.join(PARTIALS_FUNC_LISTS[locale], f'{cat}.adoc')
        cut_text = f'// Автоматически созданный файл для списка функций категории {cat}\n// Локаль: {locale}\n\n'
        for obj in objects.values():
            if obj[2] == cat:
                if obj[1] == 'operator':
                    func_name_backticks = f'Оператор `{obj[0]}`'
                    cut_text += f'** {obj[4]}[{func_name_backticks}]\n'
                elif obj[1] in ['function', 'python_function']:
                    func_name_backticks = f'{obj[0]}'
                    cut_text += f'** `{obj[4]}[{func_name_backticks}]`\n'
        with open(output_file_name, 'w', encoding='utf8') as file:
            file.write(cut_text)
        if LOG_ON:
            print(f'Created file (lines: {cut_text.count(chr(10))}): {output_file_name}')


    # Добавляем в общий список объектов функции-псевдонимы

    for func in objects_markup_dict['functions']:
        # Имя текущей функции (она псевдоним)
        cur_func = list(func.keys())[0]
        #print(cur_func)
        if 'alias_of' in func[cur_func].keys():
            # Имя главной функции для текущей
            cur_main_func = func[cur_func]['alias_of']
            # Имеющаяся запись главной функции (если она существует)
            cur_main_description = objects.get(f'{cur_main_func} function', '<empty>')
            # Раздел главной функции
            cur_section = cur_main_description[2]
            # Текст ссылки на главную функцию
            link_to_main = f'`{cur_main_description[4]}[{cur_main_func}]`'

            #print(cur_func)
            #print(cur_main_description)

            objects[f'{cur_func} function'] = [f'{cur_func}', 'function', cur_section, f"{category_dict[locale]['func_alias']} {link_to_main}.", '', '']

            if locale == 'ru':
                func_names.append(cur_func)
    #print(objects)
    # Добавляем в общий список объектов операторы-псевдонимы

    for oper in objects_markup_dict['operators']:
        # Имя текущего оператора
        cur_oper = list(oper.keys())[0]
        if 'alias_of' in oper[cur_oper].keys():
            # Имя главной функции для текущей
            cur_main_oper = oper[cur_oper]['alias_of']
            # Имеющаяся запись главной функции
            cur_main_description = objects[f'{cur_main_oper} operator']
            # Раздел главной функции
            cur_section = cur_main_description[2]
            # Текст ссылки на главную функцию
            link_to_main = f'`{cur_main_description[4]}[{cur_main_oper}]`'

            #print(cur_oper)
            #print(cur_main_description)
            objects[f'{cur_oper} operator'] = [f'{cur_oper}', 'operator', cur_section, f"{category_dict[locale]['oper_alias']} {link_to_main}.", '', '']


    # Собираем описания команд (раздел Manual)

    for paths, subdirs, files in os.walk(MANUAL_FOLDER[locale]):
        for file_name in files:

            # Полный путь текущего файла
            full_path = os.path.join(paths, file_name)
            # Имя текущей папки
            cur_folder = os.path.basename(os.path.dirname(full_path))
            
            if file_name == 'index.adoc':
                continue
            if not file_name.endswith('.adoc'):
                continue
            
            file_name_short = file_name.replace('.adoc', '')

            with open(full_path, 'r', encoding='utf8') as file:
                file_text = file.read()
            
            # Накладываем регулярку
            command_groups = [m.groupdict() for m in commands_regex.finditer(file_text)]
            
            for command in command_groups:
                cur_name = command['name']
                cur_dict = command['dict']
                cur_desc = adoc_dict[cur_dict]
                type = 'command'
                link = f'xref:ROOT:manual/{file_name}#{cur_dict}'

                objects[f'{cur_name} {type}'] = [cur_name, type, file_name_short, cur_desc, link, '']


    # Добавляем в общий список объектов типы данных

    for data_type in objects_markup_dict['types']:
        cur_data_type = list(data_type.keys())[0]
        type = 'data type'
        cur_desc = f'type_{cur_data_type}'.replace('[]', '_array')
        cur_desc = adoc_dict[cur_desc]
        cur_cat = data_type[cur_data_type]['category']
        link = f'xref:ROOT:data_types/{cur_cat}.adoc'
        
        objects[f'{cur_data_type} {type}'] = [cur_data_type.replace(']', r'\]'), type, cur_cat, cur_desc, link, '']


    # Добавляем в общий список объектов псевдонимы типов данных
    for data_type in objects_markup_dict['types']:
        #print(data_type)
        cur_data_type = list(data_type.keys())[0]
        if 'alias_of' in data_type[cur_data_type].keys():
            cur_alias = data_type[cur_data_type]['alias_of']
        else:
            cur_alias = []
        
        # Берем запись из objects для главного типа
        cur_main_description = objects[f'{cur_data_type} data type']
        # Текст ссылки на главный тип
        cur_data_type_replaced = cur_data_type.replace(']', r'\]')
        link_to_main = f'`{cur_main_description[4]}[{cur_data_type_replaced}]`'
        
        for alias in cur_alias:
            type = 'data type'
            cur_desc = f"{category_dict[locale]['type_alias']} {link_to_main}."
            cur_cat = data_type[cur_data_type]['category']
            objects[f'{alias} {type}'] = [alias, type, cur_cat, cur_desc, '', '']


    # Собираем описания запросов
    query_filenames = {
    'group_by':'group by',
    'order_by':'order by',
    'similar_to':'similar to'
    }

    for paths, subdirs, files in os.walk(QUERY_FOLDER[locale]):
        for file_name in files:

            # Полный путь текущего файла
            full_path = os.path.join(paths, file_name)
            # Имя текущей папки
            cur_folder = os.path.basename(os.path.dirname(full_path))

            if file_name == 'index.adoc':
                continue
            if not file_name.endswith('.adoc'):
                continue
            if file_name.startswith('_'):
                continue
            
            cur_name = file_name.replace('.adoc', '')

            if cur_name in query_filenames.keys():
                cur_name = query_filenames[cur_name]
            cur_name = cur_name.upper()
            type = 'query'

            # Для некоторых объектов свои уникальные описания, для остальных дефолтное
            if cur_name == 'SELECT':
                cur_desc = category_dict[locale]['select_desc']
            elif cur_name == 'EXPLAIN':
                cur_desc = category_dict[locale]['explain_desc']
            else:
                cur_desc = category_dict[locale]['query_default_desc']

            cur_cat = ''
            link = f'xref:ROOT:sql_queries/{file_name}'
        
            objects[f'{cur_name} {type}'] = [cur_name, type, cur_cat, cur_desc, link, '']

    # Добавляем описания запросов, у которых нет своей страницы
    query_no_pages = objects_markup_dict['queries']

    for query in query_no_pages:
        cur_name = list(query.keys())[0]
        cur_page = query[cur_name]['page']
        
        type = 'query'
        cur_cat = ''
        cur_desc = category_dict[locale]['query_default_desc']
        link = f'xref:ROOT:sql_queries/{cur_page}.adoc#{cur_name.lower()}'
        
        objects[f'{cur_name} {type}'] = [cur_name, type, cur_cat, cur_desc, link, '']


    #for k,v in objects.items():
    #    print(k,v)
    #    print()

    # Пишем текст алфавитного указателя
    objects_index = f'''\
// Автоматически генерируемый алфавитный указатель объектов для локали {locale}
ifndef::assembler-backend-pdf[]
[cols="1,3,10", grid=rows, frame=none]
endif::[]
ifdef::assembler-backend-pdf[]
[cols="3,3,10", grid=rows, frame=none]
endif::[]
|===

'''

    # Для подсчета объектов по категориям
    types_num = {type:0 for type in types_dict[locale].keys()}
    # Для json с докстрингами
    docstrings = []

    prod_url = 'https://tengri.postgrespro.ru/documentation/ru/stable/'

    # Сортируем итоговый словарь по алфавиту по ключам без учета регистра
    for k in sorted(objects.keys(), key=str.casefold):
        #print(k)
        obj = objects[k]
        type = obj[1]
        # Для псевдонимов и обычных функций разные входы
        if obj[4] == '':
            link_text = f'`{obj[0]}`'
        else:
            link_text = f'`{obj[4]}[{obj[0]}]`'
        link_text = link_text.replace('|',r'\|')

        description = obj[3]

        # Добавляем в конце точку, если ее нет
        description = description.rstrip()
        if not description.endswith('.'):
            description += '.'
        
        # Пишем текст в алфавитный указатель
        objects_index += f'|{link_text}\n'
        objects_index += f'|{types_dict[locale][type]}\n'
        objects_index += f'|{description}\n\n'

        # Пишем текст для AI-агентов

        # Убираем ссылки на adoc 
        description_ai = re.sub(r'xref:[^\[]*\.?adoc.*?\[(.*?)\]', r'\1', description)
        # Убираем конечные точки, чтобы экономить токены
        description_ai = description_ai.rstrip('.')
        
        # Пишем описания функций
        if types_dict[locale][type] == 'Function' and locale == 'en' and obj[4] != '':
            functions_for_ai['functions'] += f'- {obj[0]} - {description_ai}\n'
        
        # Пишем описания типов
        if types_dict[locale][type] == 'Data type' and locale == 'en' and obj[4] != '':
            # Убираем экранирование скобок в названиях типов
            type_name = obj[0].replace(r'\]', ']')
            functions_for_ai['types'] += f'- {type_name} - {description_ai}\n'

        # Пишем json для докстрингов
        if obj[5] == '':
            usage = ''
        else:
            usage = obj[5] + '\n\n'

        if obj[4] == '':
            link = ''
        else:
            link = obj[4].replace('xref:ROOT:', prod_url).replace('.adoc', '')
            link = f'\n\n[Перейти к документации]({link})'

        cur_name = obj[0]
        # Заменяем escape в именах
        cur_name = cur_name.replace('\\]', ']')

        # Заменяем ссылки xref adoc на md
        md_descripton = re.sub(r'xref:(?:ROOT:)?(?P<url>.+?)\.adoc(?P<anchor>#.+?)?\[(?P<link_text>.*?[^\\])\]',
                            fr'[\3]({prod_url}\1\2)',
                            description)
        # Убираем escape от adoc
        md_descripton = md_descripton.replace('\\', '')
        # Заменяем внешние ссылки adoc на md
        md_descripton = re.sub(r'(?P<url>http.+?)\[(?P<link_text>.+?)\]',
                            r'[\2](\1)',
                            md_descripton)
        json_description = f'{usage}{md_descripton}{link}'
        docstrings.append({'name':cur_name, 'type':obj[1], 'category':obj[2], 'description':json_description})

        # Считаем количество объектов
        types_num[type] += 1

    objects_index += f'\n|===\n\n{mes_dict[locale]["objects_total"]}: {len(objects)}'

    '''
    test_file = ''
    for d in docstrings:
        test_file += d['description'] + '\n\n\n'
    with open('test_file.md', 'w', encoding='utf8') as file:
        file.write(test_file)
    '''

    # Пишем json с докстрингами в файл
    with open(JSON_DOCSTRINGS[locale], 'w', encoding='utf8') as file: 
        json.dump(docstrings, file, indent=4, ensure_ascii=False)

    # Пишем указатель в файл
    with open(INDEX_OUTPUT[locale], 'w', encoding='utf8') as file:
        file.write(objects_index)

    # Выводим в лог информацию по количеству
    if LOG_ON:
        print(f'Created: {INDEX_OUTPUT[locale]}')
        for k,v in types_num.items():
            print(f'objects_index Type {k}: {v}')
    print(f'objects_index Total: {len(objects)}')


# Собираем текст примеров для тестов (только со страниц под functions и некоторых других)

# Текст исключений (если они есть в запросе, то такой запрос не берем)
exceptions = ['read_xlsx(filepath[']

queries_num = 0

# Пути откуда собирать - FUNCTION_FOLDER и дополнительные страницы
queries_paths = []

for paths, subdirs, files in os.walk(FUNCTION_FOLDER['ru']):
    for file_name in files:
        if file_name not in ['index.adoc', 'tengri_functions.adoc']:
            queries_paths.append(os.path.join(paths, file_name))

# Дополнительные страницы
queries_extra_files = [
'documentation-ru/modules/ROOT/pages/admin_manual.adoc',
'documentation-ru/modules/ROOT/pages/admin/user_config.adoc',
'documentation-ru/modules/ROOT/pages/admin/system_tables.adoc'
]

queries_paths += queries_extra_files

# Извлекаем примеры запросов
for full_path in queries_paths:
    
    with open(full_path, 'r', encoding='utf8') as file:
        file_text = file.read()

    # Накладываем регулярку
    cur_queries = [val for m in queries_regex.finditer(file_text) for val in m.groups()]
    
    queries_dict[full_path] = [item for item in cur_queries if not any(ex in item for ex in exceptions)]

    # Считаем количество
    queries_num += len(queries_dict[full_path])


# Пишем json с текстами примеров в файл
with open(JSON_QUERIES, 'w', encoding='utf8') as f: 
    json.dump(queries_dict, f, indent=4, ensure_ascii=False)
print(f'Queries for tests total: {queries_num}')

# Пишем описания функций для AI-агентов в файл
functions_for_ai_final = functions_for_ai['types'] + functions_for_ai['functions']
with open(FUNCTIONS_FOR_AI_FILE, 'w', encoding='utf8') as file: 
    file.write(functions_for_ai_final)
print(f"Descriptions for AI: Data types - {functions_for_ai['types'].count(chr(10))}, Functions - {functions_for_ai['functions'].count(chr(10))}")

# Учет функций из DuckDB
#duck = ['array_extract', 'array_slice', 'ascii', 'bar', 'base64', 'bin', 'bit_length', 'char_length', 'character_length', 'chr', 'concat', 'concat_ws', 'contains', 'ends_with', 'format', 'formatReadableDecimalSize', 'format_bytes', 'from_base64', 'from_binary', 'from_hex', 'greatest', 'hash', 'hex', 'ilike_escape', 'instr', 'lcase', 'least', 'left', 'left_grapheme', 'len', 'length', 'length_grapheme', 'like_escape', 'lower', 'lpad', 'ltrim', 'md5', 'md5_number', 'md5_number_lower', 'md5_number_upper', 'nfc_normalize', 'not_ilike_escape', 'not_like_escape', 'ord', 'parse_dirname', 'parse_dirpath', 'parse_filename', 'parse_path', 'position', 'position', 'prefix', 'printf', 'read_text', 'regexp_escape', 'regexp_extract', 'regexp_extract', 'regexp_extract_all', 'regexp_full_match', 'regexp_matches', 'regexp_replace', 'regexp_split_to_array', 'regexp_split_to_table', 'repeat', 'replace', 'reverse', 'right', 'right_grapheme', 'rpad', 'rtrim', 'sha1', 'sha256', 'split', 'split_part', 'starts_with', 'str_split', 'str_split_regex', 'string_split', 'string_split_regex', 'string_to_array', 'strip_accents', 'strlen', 'strpos', 'substr', 'substring', 'substring_grapheme', 'suffix', 'to_base', 'to_base64', 'to_binary', 'to_hex', 'translate', 'trim', 'ucase', 'unbin', 'unhex', 'unicode', 'upper', 'url_decode', 'url_encode']
#print(len(duck))
#for name in sorted(list(set(duck) - set(func_names))):
#    print(name)


