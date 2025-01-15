#!/usr/bin/env python3

#    Copyright 2024 Alexander Zubakha

#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import os
import logging
from sys import argv
from re import search
from pathlib import Path
from copy import deepcopy
from json import dump, loads
from time import perf_counter
from shutil import copy, move
from functools import partial
from collections import Counter
from datetime import datetime, date
from platform import platform, system
from json.decoder import JSONDecodeError
from concurrent.futures import ProcessPoolExecutor

def main():
    info_log = get_config_path('info.log')

    logging.basicConfig(filename=info_log, filemode='w', level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    logging.info('The program started working.')

    log_system_info()

    default_settings = {'paths': [], 'sorting': False, 'output_files': False,
                        'output_extensions': False, 'filter_by_size': False,
                        'indicator_output': False, 'cleaned_files_report': False}

    settings_path = get_config_path('settings.json')

    boolean = greeting(settings_path)

    if boolean:
        print('If you want to change the program settings, write "Yes".')
        act = input('If you want to continue without changing the settings, press "Enter": ')
        if act.lower().strip() == 'yes':
            select_option(settings_path, default_settings)
    else:
        continue_changes = get_paths_for_windows(default_settings, settings_path)
        if continue_changes:
            select_option(settings_path, default_settings)
        else:
            act = input('\nIf you want to continue changing the program settings, then write "Yes": ')
            if act.lower().strip() == 'yes':
                select_option(settings_path, default_settings)

    settings = check_settings(*get_json_content(settings_path, default_settings))
    paths = settings['paths']
    output_files = settings['output_files']
    output_extensions = settings['output_extensions']
    sorting = settings['sorting']
    filter_by_size = settings['filter_by_size']
    indicator_output = settings['indicator_output']
    display_stats = settings['cleaned_files_report']

    checking_paths_for_correctness(settings, settings_path)

    max_length = max([len(el) for el in paths])
    os_name = system()
    s = '\\' if os_name == 'Windows' else '/'
    list_of_selected_paths = []
    list_of_directories = []
    files_and_size = []
    list_of_files = []
    total_size = 0

    if len(paths) > 1:
        print('\nYou have the following directories to analyze:')
        for i, path in enumerate(paths, 1):
            print(f'{i}.) {path}')
    else:
        print(f'\nThe following directory is available for analysis: \n{paths[0]}')

    if len(paths) > 1:
        print('\nIf you want to analyze all directories, then write "1".')
        choice = input('If specific directories, then write "2": ').strip()
    else:
        choice = '1'

    choice = get_valid_choice(choice)

    if choice == '1':
        file_formats, inversion = input_file_format()
        list_of_selected_paths = paths

        for path in paths:
            if os_name != 'Windows':
                total = get_all_files(path, file_formats, inversion, filter_by_size, s)
            else:
                total = get_all_files_windows(path, file_formats, inversion, filter_by_size, s)
            directory = get_directories_size(path, max_length, total[0])
            list_of_directories.append(directory)
            files_and_size.extend(total[1])
            list_of_files.extend(total[2])
            total_size += total[0]

        information_output(files_and_size, list_of_files, list_of_directories, total_size,
                           output_files, output_extensions, sorting)

        boolean = execute_the_selected_option(list_of_files, list_of_selected_paths, paths,
                                              output_files, indicator_output, s)

        post_cleanup_actions(boolean, list_of_files, total_size, display_stats, s)

    elif choice == '2':
        dirs = select_directories(paths)
        file_formats, inversion = input_file_format()

        for i in dirs:
            path = paths[int(i)-1]
            if os_name != 'Windows':
                total = get_all_files(path, file_formats, inversion, filter_by_size, s)
            else:
                total = get_all_files_windows(path, file_formats, inversion, filter_by_size, s)
            directory = get_directories_size(path, max_length, total[0])
            list_of_directories.append(directory)
            list_of_selected_paths.append(path)
            files_and_size.extend(total[1])
            list_of_files.extend(total[2])
            total_size += total[0]

        information_output(files_and_size, list_of_files, list_of_directories, total_size,
                           output_files, output_extensions, sorting)

        boolean = execute_the_selected_option(list_of_files, list_of_selected_paths, paths,
                                              output_files, indicator_output, s)

        post_cleanup_actions(boolean, list_of_files, total_size, display_stats, s)

    restart_script()

def get_config_path(file_name):
    user_home = Path.home()
    os_name = system()

    if os_name == 'Linux':
        config_dir = user_home / '.config' / 'Cleaner'
    else:
        config_dir = user_home / 'Documents' / 'Cleaner'

    config_path = config_dir / file_name

    try:
        config_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        print(f'\nAccess to the following directory was denied: \n{user_home}')
        print('\nChange the permissions for this directory and restart the program.')
        logging.critical('Error while trying to access user\'s home directory!')
        exit()

    return config_path

def log_system_info():
    os_info = platform()
    working_directory = os.path.dirname(argv[0])
    logging.info(f'OS: {os_info}')
    logging.info(f'Working directory: {working_directory}')

def greeting(settings_path):
    text = '''Welcome to the Program!\n
**Overview:**
This program provides various options for managing files on your computer.\n
**Features:**
- Delete, copy, and move files based on criteria such as extension or file size.
- Select specific directories to manage files.
- Sort files alphabetically or by file size.
- Display statistics about deleted files.\n
**Note:**
Not all features of the program are described here.'''

    if not os.path.exists(settings_path):
        print(text)
        input('\nPress Enter to continue: ')
        print('\nBefore you get started, you need to configure the program and add the first directories.')
        print('Just follow the program messages.')
        return False
    else:
        return True

def select_option(settings_path, default_settings):
    options = {1: change_paths, 2: change_files_sorting, 3: files_output_mode,
               4: extensions_output_mode, 5: filter_mode_by_size, 6: indicator_output_selection,
               7: show_file_statistics}

    settings = check_settings(*get_json_content(settings_path, default_settings))

    default_settings = deepcopy(default_settings)

    print('\nThe following options are available to you:')
    if len(settings['paths']) == 0:
        print('1.) Add paths.')
    else:
        print('1.) Add or remove paths.')
    print('2.) Change the files sorting criteria.')
    if not settings['output_files']:
        print('3.) Enable output of a list of directory files.')
    else:
        print('3.) Disable output of a list of directory files.')
    if not settings['output_extensions']:
        print('4.) Enable display of file extension list.')
    else:
        print('4.) Disable display of file extension list.')
    print('5.) Filter files by size.')
    if not settings['indicator_output']:
        print('6.) Enable operation progress indicator.')
    else:
        print('6.) Turn off the operation progress indicator.')
    if not settings['cleaned_files_report']:
        print('7.) Enable the display of detailed statistics about deleted files.')
    else:
        print('7.) Disable the display of detailed statistics about deleted files.')

    if settings['sorting'] or settings['output_files'] or settings['output_extensions'] or \
        settings['filter_by_size'] or settings['indicator_output'] or settings['cleaned_files_report']:
        options[8] = get_default_settings
        print('8.) Restore all settings to default.')
        max_option = 8
    else:
        max_option = 7

    while True:
        try:
            number = int(input('\nSelect the number of the desired option: '))
            if number in options:
                break
            else:
                print(f'Please enter a number in the range from 1 to {max_option}.')
        except ValueError:
            print(f'Please enter a number in the range from 1 to {max_option}.')

    new_settings = options[number](settings)

    if new_settings:
        saving_settings(settings_path, new_settings)

    act = input('\nIf you want to continue changing the settings, write "Yes": ')
    if act.lower().strip() == 'yes':
        select_option(settings_path, default_settings)

    restart_script()

def get_paths_for_windows(settings, settings_path):
    if system() != 'Windows':
        return True

    username = os.getlogin()
    system_drive = os.getenv('SYSTEMDRIVE')
    new_settings = deepcopy(settings)

    paths = [f'{system_drive}/Windows/SoftwareDistribution/Download',
             f'{system_drive}/Users/{username}/AppData/Local/Temp',
             f'{system_drive}/Users/{username}/Downloads',
             f'{system_drive}/Windows/LiveKernelReports',
             f'{system_drive}/Users/{username}/Pictures',
             f'{system_drive}/Windows/Prefetch',
             f'{system_drive}/Windows/Temp',
             f'{system_drive}/Windows/Logs',
             f'{system_drive}/Windows/Log']

    correct_paths, _, _ = filter_valid_paths(paths)

    if len(correct_paths) > 0:
        print('\nThe following paths were found and can be saved in the program:')
        for i, path in enumerate(correct_paths, 1):
            print(f'{i}.) {path}')
    else:
        return True

    new_settings['paths'] = correct_paths

    continue_changes = saving_settings(settings_path, new_settings)

    return continue_changes

def filter_valid_paths(paths):
    correct_paths = []
    paths_not_found = []
    permission_error = []

    for path in paths:
        try:
            os.listdir(path)
            correct_paths.append(path)
        except (FileNotFoundError, TypeError, NotADirectoryError):
            paths_not_found.append(path)
        except PermissionError:
            permission_error.append(path)
            correct_paths.append(path)

    return correct_paths, paths_not_found, permission_error

def saving_settings(settings_path, settings):
    act = input('\nTo save the settings, write "Yes": ')

    if act.lower().strip() == 'yes':
        try:
            with open(settings_path, 'w') as file:
                dump(settings, file, indent=4)
                print('The settings were successfully saved.')
                return False
        except PermissionError:
            print('Error! Failed to save settings!')
            print('Check file and directory permissions and restart the program.')
            logging.critical('Error saving program settings!')
            exit()
    else:
        print('The settings were not saved.')
        return True

def get_json_content(file_path, default_config):
    try:
        with open(file_path, 'r') as file:
            data = file.read()
            content = loads(data)
            if isinstance(content, dict):
                return loads(data), default_config
            return default_config, default_config
    except (FileNotFoundError, JSONDecodeError):
        return default_config, default_config

def check_settings(settings, default_settings):
    if len(settings) != 7 or \
        'paths' not in settings or \
        'sorting' not in settings or \
        'output_files' not in settings or \
        'output_extensions' not in settings or \
        'filter_by_size' not in settings or \
        'indicator_output' not in settings or \
        'cleaned_files_report' not in settings:
        return default_settings

    if not isinstance(settings['paths'], list) or \
        settings['sorting'] not in (False, 'alphabet', 'size') or \
        not isinstance(settings['output_files'], bool) or \
        not isinstance(settings['output_extensions'], bool) or \
        not isinstance(settings['indicator_output'], bool) or \
        not isinstance(settings['cleaned_files_report'], bool):
        return default_settings

    filter_by_size = settings['filter_by_size']

    if not (not filter_by_size or \
        (isinstance(filter_by_size, list) and len(filter_by_size) == 2 and \
        all(isinstance(i, int) for i in filter_by_size) and \
        (filter_by_size[1] > filter_by_size[0] and \
        filter_by_size[0] >= 0 and filter_by_size[1] > 0))):
        return default_settings

    return settings

def change_paths(settings):
    saved_paths = settings['paths']
    options = {1: add_new_paths}

    if len(saved_paths) > 0:
        print('\nThe following options are available to you:')
        print('1.) Add new paths. \n2.) Delete selected paths.')
        options[2] = delete_selected_paths
    else:
        number = 1

    print('''\nThese options are settings for the program itself.
Any changes to the options above do not affect the paths on your computer.''')

    while True:
        try:
            if len(saved_paths) > 0:
                number = int(input('\nSelect the number of the desired option: '))
            if number in options:
                break
            else:
                print('Please select the number of the available option.')
        except ValueError:
            print('Please select the number of the available option.')

    new_settings, boolean = options[number](settings)
    new_paths = new_settings['paths']

    if len(new_paths) > 0 and new_paths != saved_paths:
        print('\nThe following paths will be saved in the program:')
        for i, path in enumerate(new_paths, 1):
            print(f'{i}.) {path}')
    elif boolean and new_paths == saved_paths:
        print('\nNew paths were not added.')
        return False
    else:
        print('\nAll paths will be deleted.')

    return new_settings

def add_new_paths(settings):
    print('\nEnter the full path you want to add.')

    while True:
        paths = input('If there are multiple paths then separate '
        'the paths with a comma along with a space: ')

        if paths.strip():
            paths = paths.split(', ')
            break
        else:
            print('Please enter path.\n')

    new_paths = [path.replace('\\', '/').strip() for path in paths]
    saved_paths = settings['paths']
    unique_paths = []

    new_paths, paths_not_found, _ = filter_valid_paths(new_paths)

    if len(paths_not_found) > 0:
        print('\nThe following new paths were not found and have been removed:')
        for i, path in enumerate(paths_not_found, 1):
            print(f'{i}.) {path}')

    for path in (saved_paths + new_paths):
        if path not in unique_paths:
            unique_paths.append(path) 

    settings['paths'] = unique_paths

    return settings, True

def delete_selected_paths(settings):
    paths = settings['paths']
    quantity = len(paths)

    if quantity > 1:
        print('\nYou have the following paths to delete:')
        for i, path in enumerate(paths, 1):
            print(f"{i}.) {path}")

    if quantity > 1:
        print('\nIf you want to delete all paths, then enter "all".')
        act = input('If specific paths, then enter the path numbers: ')
    else:
        act = '1'

    while True:
        if act.lower().strip() == 'all':
            settings['paths'] = []
            return settings, False
        else:
            try:
                my_list = [int(el) for el in act.split()]
                if all(1 <= num <= len(paths) for num in my_list) and len(my_list) > 0:
                    new_paths = [path for i, path in enumerate(paths, 1) if i not in my_list]
                    settings['paths'] = new_paths
                    return settings, False
            except ValueError:
                print('Error! The keyword "all" must be entered.')
                print(f'Or numbers must be entered in the range from 1 to {quantity}.')
            act = input('\nPlease enter the required value again: ')

def change_files_sorting(settings):
    sorting = settings['sorting']

    messages = {'alphabet': 'You have enabled alphabetical file sorting.',
                'size': 'You have enabled file sorting by size.',
                False: 'You have disabled file sorting.'}

    alphabet = 'Sort files alphabetically.'
    size = 'Sort files by size.'
    shutdown = 'Disable file sorting.'

    print('\nThe following sorting criteria are available to you:')
    if not sorting:
        print(f'1.) {alphabet} \n2.) {size}')
        options = {1: 'alphabet', 2: 'size'}
    elif sorting == 'size':
        print(f'1.) {alphabet} \n2.) {shutdown}')
        options = {1: 'alphabet', 2: False}
    elif sorting == 'alphabet':
        print(f'1.) {size} \n2.) {shutdown}')
        options = {1: 'size', 2: False}

    while True:
        try:
            number = int(input('\nSelect the number of the desired option: '))
            if number in options:
                print(messages[options[number]])
                settings['sorting'] = options[number]
                return settings
            else:
                print(f'Please enter the number of the available option.')
        except ValueError:
            print(f'Please enter the number of the available option.')

def files_output_mode(settings):
    output_files = settings['output_files']

    if output_files:
        print('\nYou have directory files output enabled.')

        act = input('If you want to disable the output of directory files, then write "Yes": ')
        if act.lower().strip() == 'yes':
            print('You have disabled files output.')
            settings['output_files'] = False
            return settings
        else:
            print('Settings were not saved.')
            return False
    else:
        print('\nYou have disabled the output of directory files.')

        act = input('If you want to enable output of directory files, then write "Yes": ')
        if act.lower().strip() == 'yes':
            print('You have enabled files output.')
            settings['output_files'] = True
            return settings
        else:
            print('Settings were not saved.')
            return False

def extensions_output_mode(settings):
    output_extensions = settings['output_extensions']

    if output_extensions:
        print('\nYou have file extension display enabled.')

        act = input('If you want to disable the display of file extensions, then type "Yes": ')
        if act.lower().strip() == 'yes':
            print('You have disabled the display of file extensions.')
            settings['output_extensions'] = False
            return settings
        else:
            print('Settings were not saved.')
            return False
    else:
        print('\nYou have file extension display disabled.')

        act = input('If you want to enable the display of file extensions, then type "Yes": ')
        if act.lower().strip() == 'yes':
            print('You have enabled the display of file extensions.')
            settings['output_extensions'] = True
            return settings
        else:
            print('Settings were not saved.')
            return False

def filter_mode_by_size(settings):
    filter_by_size = settings['filter_by_size']

    if not filter_by_size:
        print('\nYou can specify a range for filtering files by size.')
        unit = select_unit()
    else:
        x, y = filter_by_size[0], filter_by_size[1]
        print(f'\nYou have a file range from {get_size(x)} to {get_size(y)}.')
        print('You can change the range for filtering files by size.')
        unit = select_unit()
        print('If you want to disable file size filtering, write "0" in each range.')

    while True:
        try:
            x = float(input('\nEnter the starting range size: '))
            y = float(input('Enter the end range size: '))
            start_range, end_range = int(x * unit), int(y * unit)

            if start_range == 0 and end_range == 0 and filter_by_size:
                print('You have disabled file size filtering.')
                settings['filter_by_size'] = False
                return settings
            if start_range < end_range and start_range >= 0 and end_range > 0:
                print(f'You have selected a range from {get_size(start_range)} to {get_size(end_range)}')
                settings['filter_by_size'] = [start_range, end_range]
                return settings
            if start_range == 0 and end_range == 0 and not filter_by_size:
                print('You have canceled your file filtering changes.')
                return False
            elif start_range == end_range:
                print('Range values must not be equal to each other.')
            elif start_range < 0 or end_range < 0:
                print('Please enter a positive number.')
            elif start_range > end_range:
                print('The starting number must be less than the ending number.')
        except ValueError:
            print('Please enter a number.')

def select_unit():
    units = {1: 1, 2: 2**10, 3: 2**20, 4: 2**30}
    unit_names = {1: 'bytes', 2: 'kilobytes', 3: 'megabytes', 4: 'gigabytes'}

    print('\nThe following units are available to you:')
    print('1.) Bytes.\n2.) Kilobytes.\n3.) Megabytes.\n4.) Gigabytes.')

    while True:
        try:
            num = int(input('\nSelect the digit of the desired unit: '))
            if num in units:
                print(f'You have selected {unit_names[num]}.')
                return units[num]
            else:
                print('Please select a number from 1 to 4.')
        except ValueError:
            print('Please select a number from 1 to 4.')

def get_size(size):
    kb, mb, gb = 2**10, 2**20, 2**30

    if size < kb:
        return f'{size}b'
    elif size < mb:
        return f'{int(size/kb)}kb'
    elif size < gb:
        return f'{round(size/mb, 1)}mb'
    else:
        return f'{round(size/gb, 1)}gb'

def indicator_output_selection(settings):
    indicator_output = settings['indicator_output']

    if indicator_output:
        print('\nYou have the operation progress indicator turned on.')
        act = input('If you want to turn off the progress indicator, then write "Yes": ')

        if act.lower().strip() == 'yes':
            print('You have turned off the operation progress indicator.')
            settings['indicator_output'] = False
            return settings
        else:
            print('Settings were not saved.')
            return False
    else:
        print('\nYour operation progress indicator is turned off.')
        print('Attention! This option may affect program performance.')
        print('The progress indicator will work when the file output option is disabled.')
        act = input('\nIf you want to enable the progress indicator, then write "Yes": ')

        if act.lower().strip() == 'yes':
            print('You have enabled the output of the operation progress indicator.')
            settings['indicator_output'] = True
            return settings
        else:
            print('Settings were not saved.')
            return False

def show_file_statistics(settings):
    cleaned_files_report = settings['cleaned_files_report']

    if cleaned_files_report:
        print('\nYou have statistics enabled for the output of deleted files.')
        act = input('If you want to disable statistics on deleted files then write "Yes": ')

        if act.lower().strip() == 'yes':
            print('You have disabled the display of statistics on deleted files.')
            settings['cleaned_files_report'] = False
            return settings
        else:
            print('Settings were not saved.')
            return False
    else:
        print('\nYou have disabled statistics for outputting deleted files.')
        print('\nWhen you enable this option, you have access to:')
        print('- Display the date of the first and last deletion of files.')
        print('- Display the total number of deleted files for the entire period.')
        print('- Display the number of deletions for the entire period.')
        print('- Display the total size of all deleted files for the entire period.')

        act = input('\nIf you want to enable statistics on deleted files then write "Yes": ')
        if act.lower().strip() == 'yes':
            print('You have enabled the display of statistics on deleted files.')
            settings['cleaned_files_report'] = True
            return settings
        else:
            print('Settings were not saved.')
            return False

def get_default_settings(settings):
    data_path = get_config_path('data.json')
    boolean = False

    act = input('\nIf you want to return the settings to default, then write "Yes": ')
    if act.lower().strip() == 'yes':
        settings['sorting'] = False
        settings['output_files'] = False
        settings['output_extensions'] = False
        settings['filter_by_size'] = False
        settings['indicator_output'] = False
        settings['cleaned_files_report'] = False
        print('Settings returned to default.')
        boolean = True
    else:
        print('The settings have not been changed.')

    if settings['paths']:
        act = input('\nIf you want to remove saved directories from the program then write "Yes": ')
        if act.lower().strip() == 'yes':
            print('Directories were removed from the program.')
            settings['paths'] = []
            boolean = True
        else:
            print('Directories were not removed from the program.')

    if os.path.exists(data_path):
        act = input('\nIf you want to clear the history of deleted files then write "Yes": ')
        if act.lower().strip() == 'yes':
            print('Are you sure you want to clear the history of deleted files?')
            act = input('To confirm the action, write "Yes": ')
            if act.lower().strip() == 'yes':
                try:
                    os.remove(data_path)
                    print('The history of deleted files has been cleared.')
                except OSError:
                    print('Error! Failed to clear history of deleted files.')
        if act.lower().strip() != 'yes':
            print('The history of deleted files was not cleared.')

    if boolean:
        return settings
    return False

def restart_script():
    act = input('\nRestart the script? To restart, write "Yes": ')
    if act.lower().strip() == 'yes':
        print('-' * 120)
        error_handler(main)
    else:
        print('The program has completed its work.')
        logging.info('The program stopped working.')
        exit()

def error_handler(main):
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print('\nYou terminated the program using a key combination.')
        logging.info('The program stopped working.')
        exit()

def checking_paths_for_correctness(settings, settings_path):
    paths = settings['paths']

    if len(paths) == 0:
        print('\nYou have not specified any path for the program.')
        restart_script()

    correct_paths, paths_not_found, permission_error = filter_valid_paths(paths)

    if len(paths_not_found) > 0:
        print('\nThe following paths were not found and have been removed:')
        for i, path in enumerate(paths_not_found, 1):
            print(f'{i}.) {path}')

        settings['paths'] = correct_paths

        saving_settings(settings_path, settings)

    if len(permission_error) > 0:
        print('\nAccess to the following directory paths is denied:')
        for i, path in enumerate(permission_error, 1):
            print(f'{i}.) {path}')
        print('\nRun the program as administrator or delete paths.')

    if len(paths_not_found) + len(permission_error) > 0:
        restart_script()

def get_valid_choice(act):
    while True:
        if act.isdigit() and act in ['1', '2']:
            return act
        act = input('\nPlease select number 1 or 2: ').strip()

def input_file_format():
    print('\nIf you want to select all files, write "all".')
    print('If there is a specific extension, then write the extension.\n')
    form = input('''If you want to enter several extensions, '''
'''then enter the extensions separated by commas and a space: ''').lower().strip()

    while True:
        if not form:
            form = input('\nPlease enter the format, not an empty line: ').lower().strip()
        else:
            break

    if form != 'all':
        form = tuple(form.split(', '))

        print('\nIf you want to select files with the selected extension, enter "1".')
        act = input('''If you want to select all files '''
'''except those with the selected extension, enter "2": ''').strip()

        act = get_valid_choice(act)

        if act == '1':
            return form, False
        elif act == '2':
            return form, True
    else:
        return form, False

def get_file_by_format(file, file_formats, inversion):
    if file_formats != 'all':
        pattern = r"\.([^./\\]{1,10})$"
        valid_extension = search(pattern, file)
        if valid_extension:
            extension = valid_extension.group(1)
        else:
            return False
        if extension in file_formats:
            boolean = True
        else:
            boolean = False
        if inversion:
            return not boolean
        return boolean
    else:
        return True

def get_all_files(path, file_formats, inversion, filter_by_size, s):
    num_cores = os.cpu_count()
    counter = 0
    total_size = 0
    files_and_size = []
    list_of_full_file_paths = []
    tasks = [[] for _ in range(num_cores)]

    for root, _, files in os.walk(path):
        task_number = counter % num_cores
        counter += 1
        tasks[task_number].append((root, files))

    get_filtered_files = partial(get_information_about_files, file_formats, inversion, filter_by_size, s)

    with ProcessPoolExecutor(max_workers=num_cores) as executor:
        data = executor.map(get_filtered_files, tasks)

        for x, y, z in data:
            total_size += x
            files_and_size.extend(y)
            list_of_full_file_paths.extend(z)

    return total_size, files_and_size, list_of_full_file_paths

def get_all_files_windows(path, file_formats, inversion, filter_by_size, s):
    total_size = 0
    files_and_size = []
    list_of_full_file_paths = []

    for root, _, files in os.walk(path):
        for file in files:
            full_file_path = os.path.join(root, file)
            format_verification = get_file_by_format(full_file_path, file_formats, inversion)

            if format_verification and os.path.exists(full_file_path):
                file_name = full_file_path.split(s)[-1]
                file_size = os.path.getsize(full_file_path)
                if not filter_by_size or filter_by_size[0] <= file_size <= filter_by_size[1]:
                    total_size += file_size
                    list_of_full_file_paths.append(full_file_path)
                    files_and_size.append((file_name, file_size))

    return total_size, files_and_size, list_of_full_file_paths

def get_information_about_files(file_formats, inversion, filter_by_size, s, directories_and_files):
    list_of_full_file_paths = []
    files_and_size = []
    total_size = 0

    for directory_and_files in directories_and_files:
        directory, files = directory_and_files[0], directory_and_files[1]
        for file in files:
            full_file_path = os.path.join(directory, file)
            format_verification = get_file_by_format(full_file_path, file_formats, inversion)

            if format_verification and os.path.exists(full_file_path):
                file_name = full_file_path.split(s)[-1]
                file_size = os.path.getsize(full_file_path)
                if not filter_by_size or filter_by_size[0] <= file_size <= filter_by_size[1]:
                    total_size += file_size
                    list_of_full_file_paths.append(full_file_path)
                    files_and_size.append((file_name, file_size))

    return total_size, files_and_size, list_of_full_file_paths

def get_directories_size(path, length, size):
    space = ' ' * (length - len(path))
    return f'{path}   {space}  {get_size(size)}'

def information_output(files_and_size, list_of_files, list_of_directories, total_size,
                       output_files, output_extensions, sorting):

    if output_extensions:
        sorted_extensions, count_of_extensions = get_file_extensions(list_of_files)

    if len(files_and_size) == 0:
        print('\nFiles were not found in directories.')
        restart_script()

    if sorting == 'alphabet' and output_files:
        files_and_size = sorted(files_and_size, key=lambda x: x[0].lower())
    elif sorting == 'size' and output_files:
        files_and_size = sorted(files_and_size, key=lambda x: x[1])

    if output_files:
        print('\nList of file names:')
        for i, file in enumerate(files_and_size, 1):
            file_name = file[0]
            file_size = get_size(file[1])
            space = ' ' * (120 - len(file_name) + (6 - len(str(i))))
            print(f'{i}.) {file_name}   {space}  {file_size}')

    if output_extensions and len(sorted_extensions) > 0:
        print('\nList of all file extensions:')
        for i, extension in enumerate(sorted_extensions, 1):
            print(f'{i}.) {extension}: {count_of_extensions[extension]}')

    if len(list_of_directories) > 1:
        print('\nWeight of each individual directory:')
        for directory in list_of_directories:
            print(directory)
    elif len(list_of_directories) == 1:
        print(f'\nTotal directory weight: \n{list_of_directories[0]}')

    if len(list_of_directories) != 1:
        print(f'Weight of all directories: {get_size(total_size)}.')

    if not output_files:
        print(f'Total {len(files_and_size)} files.')

def get_file_extensions(files):
    pattern = r"\.([^./\\]{1,10})$"
    extensions = []

    for file in files:
        valid_extension = search(pattern, file)
        if valid_extension:
            extension = valid_extension.group(1)
            extensions.append(extension)

    count_of_extensions = Counter(extensions)
    sorted_extensions = sorted(count_of_extensions, key=lambda x: count_of_extensions[x], reverse=True)

    return sorted_extensions, count_of_extensions

def execute_the_selected_option(list_of_files, list_of_selected_paths, paths, output_files, indicator_output, s):
    number, act = None, None
    words = ['copy', 'move', 'delete']

    if len(paths) != 1:
        number = selecting_an_option_for_files()
        word = words[int(number)-1]
        print(f'You have chosen to {word} files.')

    if len(paths) == 1 or number == '3':
        act = input('\nIf you want to confirm cleaning files, enter "Yes": ')
        if act.lower().strip() == 'yes':
            print('Are you sure you want to clear the selected directories?')
            act = input('To confirm the action, write "Yes": ').lower().strip()

    if act != 'yes' and act is not None:
        print('Files are not cleared.')
        return

    if act == 'yes':
        start_time = perf_counter()
        deleting_files_and_directories(list_of_files, list_of_selected_paths, output_files, indicator_output, s)
        end_time = perf_counter()
        files_cleanup_time(start_time, end_time)
        return True
    elif number in ['1', '2']:
        copy_or_move_files(list_of_files, paths, number, output_files, indicator_output, s)

def selecting_an_option_for_files():
    print('\nThe following options are available to you:')
    print('1.) Copy files. \n2.) Move files. \n3.) Delete files.')

    while True:
        act = input('\nSelect the number of the available option: ')
        if act.strip() in ['1', '2', '3']:
            return act
        print('Please select a number from 1 to 3.')

def copy_or_move_files(list_of_files, paths, number, output_files, indicator_output, s):
    word = ['copy', 'copied'] if number == '1' else ['move', 'moved']
    folder_numbers = [str(el) for el in range(1, len(paths)+1)]
    total, operations = len(list_of_files), 0
    success = True

    print('\nThe following directories are available to you:')
    for i, path in enumerate(paths, 1):
        print(f'{i}.) {path}')

    while True:
        choice = input(f'\nSelect the desired directory number to {word[0]} files: ')
        if choice.strip() in folder_numbers:
            dst = paths[int(choice)-1]
            print(f'You have selected the following directory: \n{dst}')
            break
        print(f'Please select a number from 1 to {len(paths)}.')

    choice = input('\nIf you want to confirm this action, write "Yes": ')
    if choice.lower().strip() != 'yes':
        print('The action was cancelled.')
        return

    try:
        os.listdir(dst)
    except OSError:
        print('The selected directory no longer exists.')
        print(f'Failed to {word[0]} files.')
        restart_script()

    for src in list_of_files:
        try:
            if not output_files and indicator_output:
                operations += 1
                progress_of_operations(total, operations)
            if number == '1':
                copy(src, dst)
            elif number == '2':
                move(src, dst)
        except OSError:
            success = False
            if output_files:
                print(f'File "{src.split(s)[-1]}" could not be {word[1]}.')

    if success:
        print(f'\n- The files were successfully {word[1]} to another directory.')
    else:
        print(f'\n- Not all files were successfully {word[1]} to another directory.')

def deleting_files_and_directories(list_of_files, paths, output_files, indicator_output, s):
    total, operations = len(list_of_files), 0
    success = True

    for file in list_of_files:
        try:
            if not output_files and indicator_output:
                operations += 1
                progress_of_operations(total, operations)
            os.remove(file)
        except FileNotFoundError:
            success = False
            if output_files:
                print(f'File "{file.split(s)[-1]}" not found.')
        except PermissionError:
            success = False
            if output_files:
                print(f'File "{file.split(s)[-1]}" could not be deleted.')

    for path in paths:
        for root, dirnames, _ in os.walk(path, topdown=False):
            for nested_dir in dirnames:
                subdirectory = os.path.join(root, nested_dir)
                try:
                    os.rmdir(subdirectory)
                except OSError:
                    pass

    if success:
        print('\n- Files successfully cleared.')
    else:
        print('\n- Not all files were successfully cleared.')

def progress_of_operations(total, operations):
    percents = round(operations / (total / 100))
    percents = 100 if percents > 100 else percents
    progress_bar = f"{'-' * percents}{' ' * (100 - percents)}"
    space = f'{(3 - len(str(percents))) * ' '}'

    print() if operations == 1 else ...
    print(f'\rProgress: {percents}%{space} [{progress_bar}]', end ='')
    print() if operations == total else ...

def files_cleanup_time(start_time, end_time):
    execution_time = end_time - start_time

    if execution_time < 1:
        execution_time = round(execution_time, 2)
    elif execution_time < 10:
        execution_time = round(execution_time, 1)
    elif execution_time >= 10:
        execution_time = round(execution_time)

    if execution_time < 60:
        print(f'- The files were cleared in {execution_time} seconds.')
    elif execution_time >= 60:
        minutes, seconds = execution_time // 60, execution_time % 60
        print(f'- The files were cleared in {minutes} minutes and {seconds} seconds.')

def select_directories(paths):
    while True:
        dirs = input('\nWrite the numbers of the specified directories separated by spaces: ').split()
        if all(el.isdigit() and 1 <= int(el) <= len(paths) for el in dirs) and len(dirs) != 0:
            dirs = list(set(dirs))
            return dirs
        else:
            print(f'Please enter only numbers from 1 to {len(paths)}.')

def post_cleanup_actions(boolean, list_of_files, total_size, display_stats, s):
    if boolean:
        current_date_and_time = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        information = get_information_about_deleted_files(list_of_files, total_size)
        deleted_files, not_deleted_files, total_files, total_size = information
        should_save_history = save_and_display_cleanup_info(total_files, total_size, display_stats)
        if should_save_history:
            saving_history_of_deleted_files(current_date_and_time, deleted_files, not_deleted_files, s)

def get_information_about_deleted_files(list_of_files, total_size):
    deleted_files = []
    not_deleted_files = []
    total_files = len(list_of_files)

    for file in list_of_files:
        try:
            file_size = os.path.getsize(file)
            not_deleted_files.append(file)
            total_size -= file_size
            total_files -= 1
        except OSError:
            deleted_files.append(file)

    return deleted_files, not_deleted_files, total_files, total_size

def save_and_display_cleanup_info(total_files, total_size, display_stats):
    months = {1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
              7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"}

    default_data = {'date_of_first_deletion': '0001-01-01',
                    'date_of_last_deletion': '0001-01-01',
                    'number_of_deletions': 0,
                    'number_of_deleted_files': 0,
                    'total_weight_of_deleted_files': 0}

    data_path = get_config_path('data.json')
    data = check_data(*get_json_content(data_path, default_data))

    if data['date_of_first_deletion'] == '0001-01-01':
        data['date_of_first_deletion'] = str(date.today())
        data['date_of_last_deletion'] = str(date.today())

    print(f'- {get_size(total_size)} of files have been deleted.')

    data['number_of_deletions'] += 1
    data['number_of_deleted_files'] += total_files
    data['total_weight_of_deleted_files'] += total_size

    first_date = data['date_of_first_deletion']
    last_date = data['date_of_last_deletion']
    count_of_deletions = data['number_of_deletions']
    count_of_files = data['number_of_deleted_files']
    total_weight_of_all_files = get_size(data['total_weight_of_deleted_files'])

    year_1, month_1, day_1 = map(int, first_date.split('-'))
    year_2, month_2, day_2 = map(int, last_date.split('-'))
    difference = date.today() - date(year_2, month_2, day_2)

    if display_stats:
        print(f'\n- Date of first deletion: {day_1} {months[month_1]} {year_1}')
        print(f'- Date of last deletion: {day_2} {months[month_2]} {year_2}')
        if difference.days > 0:
            word = 'day' if difference.days == 1 else 'days'
            print(f'- Files were cleared {difference.days} {word} ago.')
        print(f'\n- There were {count_of_deletions} deletions in total over the entire period of time.')
        print(f'- A total of {count_of_files} files were deleted over the entire period of time.')
        print(f'- A total of {total_weight_of_all_files} of files were deleted over the entire period of time.')

    data['date_of_last_deletion'] = str(date.today())

    should_save_history = saving_data(data_path, data)

    return should_save_history

def check_data(data, default_data):
    if len(data) != 5 or \
        'date_of_first_deletion' not in data or \
        'date_of_last_deletion' not in data or \
        'number_of_deletions' not in data or \
        'number_of_deleted_files' not in data or \
        'total_weight_of_deleted_files' not in data:
        return default_data

    my_dates = (data['date_of_first_deletion'], data['date_of_last_deletion'])
    numbers = (data['number_of_deletions'], data['number_of_deleted_files'], data['total_weight_of_deleted_files'])

    if not is_valid_dates(my_dates) or not all(isinstance(num, int) and num >= 0 for num in numbers):
        return default_data

    return data

def is_valid_dates(my_dates):
    list_of_dates = []

    for my_date in my_dates:
        if not isinstance(my_date, str):
            return False
        try:
            year, month, day = map(int, my_date.split('-'))
            list_of_dates.append(date(year, month, day))
        except (ValueError, TypeError):
            return False

    if list_of_dates[0] > list_of_dates[1] or list_of_dates[1] > date.today():
        return False
    return True

def saving_data(data_path, data):
    try:
        with open(data_path, 'w') as file:
            dump(data, file, indent=4)
            return True
    except PermissionError:
        print('\nError! Failed to save statistics data!')
        print('Check file and directory permissions.')
        logging.error('Error saving program data.')
        return False

def saving_history_of_deleted_files(current_date_and_time, deleted_files, not_deleted_files, s):
    history_of_deleted_files = get_config_path('History of deleted files.txt')
    sorted_extensions, count_of_extensions = get_file_extensions(deleted_files)
    total_files = len(deleted_files) + len(not_deleted_files)

    act = input('\nIf you want to save the history of deleted files, enter "Yes": ')
    if act.lower().strip() == 'yes':
        try:
            with open(history_of_deleted_files, "w", encoding='utf-8') as file:
                file.write(f'File deletion history date: {current_date_and_time}\n')

                if len(deleted_files) > 0:
                    file.write('\nList of deleted files:\n')
                    for i, element in enumerate(deleted_files, 1):
                        file.write(f'{i}.) {element.split(s)[-1]}\n')
                if len(not_deleted_files) > 0:
                    file.write('\nList of files that were not deleted:\n')
                    for i, element in enumerate(not_deleted_files, 1):
                        file.write(f'{i}.) {element.split(s)[-1]}\n')
                    file.write(f'\n{len(deleted_files)} out of {total_files} files were successfully deleted.\n')
                if len(sorted_extensions) > 0:
                    file.write('\nList of number of removed extensions:\n')
                    for i, extension in enumerate(sorted_extensions, 1):
                        file.write(f'{i}.) {extension}: {count_of_extensions[extension]}\n')

                print('\nThe history of deleted files has been successfully saved to the following path:')
                print(history_of_deleted_files)
        except PermissionError:
            print('Error! Failed to save history of deleted files.\n')
            print('Check file and directory permissions.')
            logging.error('Error saving history of deleted files.')
    else:
        print('The history of deleted files was not saved.')

if __name__ == '__main__':
    error_handler(main)