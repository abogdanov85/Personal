"""
В этом скрипте мы преобразуем переведенные docstrings "старого" формата в новый формат

Подробное описание "нового" формата выгруженных docstrings см. здесь: 
https://wiki.yandex.ru/engee/dokumentacija/razrabotka-dokumentacii/julia-dokumentacija/opisanie-formata-perevedennyx-docstrings/

Первая порция документов была отдана на перевод еще до того, как стало понятно, каким должен быть формат docstrings.
Поэтому пришлось написать эту конвертацию, чтобы преобразовать переведенные docstrings из старого варианта формата в новый.
Это преобразование не всегда однозначно. Скрипт преобразует все блоки, которые может, а по оставшимся выдает подробный лог,
с помощью которого можно в ручную дообработать документы.

Надеемся, что этот скрипт нам больше не понадобится, так как следующие версии будут отдаваться на перевод сразу в новом формате.

Для работы скрипта необходимо иметь два аналогичных документа в старом и новом форматах. 
В результате документ в старом формате преобразуется в новый с сохранением всех текстов описания, 
но с новыми ссылками на объекты(@binding и @typesig)

Запуск скрипта производится без параметров: 
python convert_docstrings.py
"""

import os
import re

# Задаем имя файла для конвертации
file_name = 'base.md'

# Задаем пути для двух аналогичных документов (source - новый формат, target - старый формат)
source_path = r"C:\Users\bidon\OneDrive\Документы\Ритм\Docstrings\v1.8.5_4_NewFromat"
target_path = r"C:\Users\bidon\OneDrive\Документы\Ритм\Translated_Files\v1_8_5_Docstrings_From_Translators"

source = os.path.normpath(source_path) + '\\' + file_name
target = os.path.normpath(target_path) + '\\' + file_name
#print()
#print(source)

with open(source, 'r', encoding='utf8') as file:
    data = file.read()
    #print(data)

# Считаем кавычки и объекты 
count_quotes = len(re.findall(r'"""', data))
print()
print('Count of """ in source: ', count_quotes)
print('Count of objects in source: ', count_quotes/2)

# Парсим файл с новым форматом
#reg = r'\"\"\"\n(\s{4})?(?P<group1>.*?)\n(?P<group2>[\s\S]*?)\"\"\"\n@binding:\s(?P<group3>.*?)\n@typesig:\s(?P<group4>.*?)\n'

r = re.compile('\"\"\"\n(\s{4})?(?P<group1>.*?)\n(?P<group2>[\s\S]*?)\"\"\"\n@binding:\s(?P<group3>.*?)\n@typesig:\s(?P<group4>.*?)\n')
res = [m.groupdict() for m in r.finditer(data)]

list_first_string = []
list_binding = []
list_typesig = []


# Сохраняем в списки отдельно первые строки, байндинги и тайпсиги
for item in res:
    list_first_string.append(item['group1'])
    list_binding.append(item['group3'])
    list_typesig.append(item['group4'])

print('Found first strings in source: ', len(list_first_string))
print()

#for l in list_first_string:
#    print(l)

dict_source = {}
dict_source_simple = {}

# Делаем вложенный словарь соответствий
for i in range(len(list_first_string)):
    dict_source[list_first_string[i]] = {'binding':list_binding[i], 'typesig':list_typesig[i]}
#print(dict_source) 

# Упрощенный словарь без первых строк
for i in range(len(list_binding)):
    dict_source_simple[list_binding[i]] = list_typesig[i]
#print(dict_source_simple) 


# Переходим к файлу, который нужно конвертить

with open(target, 'r', encoding='utf8') as file2:
    data_target = file2.read()
#print()
#print('Target file:', target)

#count_to_replace = len(re.findall(r'\n\n\s\s\s\s', data_target))
#print('Count to replace: ', count_to_replace)

count_quotes = len(re.findall(r'"""', data_target))
print('Count of """ in target: ', count_quotes)
print('Count of objects in target: ', count_quotes/2)

count_first_lines = 0

prev_line = '@@@@@@@@'

# Ищем первые строки и метим их
lines = data_target.splitlines()
lines_ed = []
for line in lines:
    if line[4:] in list_first_string and prev_line == '"""':
        #print(line)
        line_ed = re.sub(r'\s{4}', r'    @@@@', line)
        #print(line_ed)
        count_first_lines += 1
    # Выкалываем некоторые случаи, где первая строка - короткое частое слово
    elif (line[4:] in list_first_string) and (prev_line == '') and (not line[4:] in ['let', '...']):
        #print(line)
        line_ed = re.sub(r'\s{4}', r'    @@@@', line)
        #print(line_ed)
        count_first_lines += 1
    else: line_ed = line
    lines_ed.append(line_ed)
    prev_line = line
# Чтобы в конце точно была пустая строка
lines_ed.append(' ')
data_target = '\n'.join(lines_ed)
#print(data_target)

print('Count of found first strings in target: ', count_first_lines)

#with open('test_result.txt', 'w', encoding='utf8') as file5:
#    file5.write(data_target)

# Первый проход - добавляем @@PLACE на месте новых binding
data_target_tuple = re.subn(r'\n\n[^\S\r\n]{4}@{4}', r'\n\n"""\n@@PLACE\n\n\n"""\n    ', data_target)
#print(data_target_tuple[0])
data_target = data_target_tuple[0]
print('Added @@PLACE: ', data_target_tuple[1])

# Удаляем метки @@@@
data_target_tuple = re.subn(r'@{4}', r'', data_target)
data_target = data_target_tuple[0]
print('Removed @@@@: ', data_target_tuple[1])

#with open('test_result4.txt', 'w', encoding='utf8') as file4:
#    file4.write(data_target)

all_done = False
replace_count = 0
replaces = {}

# Заменяем @@PLACE на ближайший binding, пока не заменим все 
# (в случае множественных блоков нужно проходить неограниченное количество раз)
while not all_done:
    data_target_tuple = re.subn(r'@@PLACE(?P<group1>[\s\S]*?)\"\"\"\n(?P<group2>[^\s@].*?)\n', 
                r'\2\1"""\n\2\n', 
                data_target)
    data_target = data_target_tuple[0]
    replace_count += data_target_tuple[1]
    if data_target_tuple[1] == 0:
        all_done = True

print('Replaced @@PLACE: ', replace_count)

#print(data_target)

count_check = len(re.findall(r'@@PLACE', data_target))
print('Count check: ', count_check)

count_quotes = len(re.findall(r'"""', data_target))
print('Count of """ after replaces: ', count_quotes)
print('Count of objects after replaces: ', count_quotes/2)
print()

#with open('test_result5.txt', 'w', encoding='utf8') as file5:
#    file5.write(data_target)

lines = data_target.splitlines()
#print(lines[0:5])
#lines.insert(2, 'test')
#print(lines[0:5])

prev = ''
i = 0
cur_binding = '@@@'
cur_typesig = '@@@'
binding_added = 0
typesig_added = 0
count_bad = 0
count_reverse = 0
count_normal = 0
count_exception = 0

# Делаем замены под новый формат
while i < len(lines):
    if lines[i].startswith('    ') and prev == '"""':
        #print('first line:', lines[i][4:])
        cur_first_line = lines[i][4:]
        cur_binding = dict_source[cur_first_line]['binding']
        #print(cur_binding)
        cur_typesig = dict_source[cur_first_line]['typesig']
        #print(cur_typesig)
    
    #if lines[i].endswith(cur_binding) and prev == '"""':
    # Новый binding является частью старого
    elif (lines[i][:3] != '   ') and (prev == '"""') and (cur_binding in lines[i]):
        #print()
        #print('Found binding:', lines[i])
        lines[i] = '@binding: ' + cur_binding
        binding_added += 1
        lines.insert(i+1, '@typesig: ' + cur_typesig)
        typesig_added += 1
        count_normal += 1
        #print()
        #print('Found without spaces')
    
    # Старый binding является частью нового
    elif (lines[i][:3] != '   ') and (prev == '"""') and (lines[i] in cur_binding):
        #print('cur_binding: ', cur_binding)
        #print('lines[i]: ', lines[i])
        lines[i] = '@binding: ' + cur_binding
        binding_added += 1
        lines.insert(i+1, '@typesig: ' + cur_typesig)
        typesig_added += 1
        count_reverse += 1
    
    # Прочие случаи
    elif (lines[i][:3] != '   ') and (prev == '"""') and (not lines[i] in list_first_string):
        if lines[i] in dict_source_simple:
            new_binding = lines[i]
            new_typesig = dict_source_simple[lines[i]]
            #print()
            #print('new_binding', new_binding)
            #print('new_typesig', new_typesig)
            lines[i] = '@binding: ' + new_binding
            binding_added += 1
            lines.insert(i+1, '@typesig: ' + new_typesig)
            typesig_added += 1
            count_exception += 1
        else:
            #print()
            #print('cur_first_line: ', cur_first_line)
            #print('cur_binding: ', cur_binding)
            print('Binding not found for:', lines[i])
            count_bad += 1
    elif (prev == '"""'):
        print('Also check line:')
        print(lines[i])
        print('Line: ', i)
        #print('cur_first_line: ', cur_first_line)
        #print('cur_binding: ', cur_binding)
        #print()
    
    prev = lines[i]
    i += 1

print()
print('count_normal:', count_normal)
print('count_reverse:', count_reverse)
print('count_exception:', count_exception)
print('count_bad:', count_bad)

converted_file = 'converted_' + file_name
with open(converted_file, 'w', encoding='utf8', newline='\u000A') as file3:
    file3.write('\n'.join(lines))

print('Binding added:', binding_added)
print('Typesig added:', typesig_added)
print('Result: ', converted_file)