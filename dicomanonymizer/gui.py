import warnings

from PySide2.QtWidgets import QApplication, QLabel, QWidget, QCheckBox, QLineEdit, QFileSystemModel, QPushButton, QListView, QTableWidget, QTableWidgetItem, QMessageBox
from PySide2.QtWidgets import QGridLayout, QVBoxLayout, QHBoxLayout, QToolButton, QGroupBox, QFileDialog, QProgressDialog, QAbstractItemView, QHeaderView, QStyleOptionViewItem
from PySide2.QtCore import Qt, QSize, QModelIndex, QUrl
from PySide2.QtGui import QIcon, QPixmap, QPainter, QColor, QDesktopServices

from datetime import datetime

import os, sys
import ast

from dicomanonymizer.anonymizer import generate_actions, anonymize_dicom_file, actions_map_name_functions
import json

ROOT_PATH = os.path.split(os.path.dirname(os.path.realpath(__file__)))[0]


class OptionsWidget:
    def __init__(self):
        # Options
        self.cb_keep_private_tags = QCheckBox("Keep Private Tags")
        self.button_fix_output_dir = QPushButton("Select output folder")
        self.button_fix_output_dir.setCheckable(True)
        self.output_folder = FileSelector(button_label='Select directory', directory=True)
        self.output_folder.setHidden(True)
        self.button_fix_output_dir.clicked.connect(lambda: self.output_folder.setHidden(not self.button_fix_output_dir.isChecked()))
        self.label_tag_actions = QLabel('Tag actions (comma separated)')
        self.line_tag_actions = QLineEdit()
        self.line_tag_actions.setText("(0x0010,0x0020);replace_UID")
        self.dict_file_widget = FileSelector(label='Dictionary', button_label='...', selection_filter='JSON (*.json)')

        self._layout_tag_actions = QHBoxLayout()
        self._layout_options = QVBoxLayout()
        self.container_box = QGroupBox()

        self.build_layouts()

    def build_layouts(self):
        # Options layouts
        self._layout_tag_actions.addWidget(self.label_tag_actions)
        self._layout_tag_actions.addWidget(self.line_tag_actions)

        self._layout_options.alignment()
        self._layout_options.addWidget(self.cb_keep_private_tags)
        self._layout_options.addLayout(self._layout_tag_actions)
        self._layout_options.addWidget(self.dict_file_widget)
        self._layout_options.setAlignment(Qt.AlignTop)
        self._layout_options.addWidget(self.button_fix_output_dir)
        self._layout_options.addWidget(self.output_folder)
        self.container_box.setLayout(self._layout_options)
        self.container_box.setMinimumWidth(400)
        self.container_box.setFixedHeight(200)

    def setEnabled(self, arg__1: bool):
        self.line_tag_actions.setEnabled(arg__1)
        self.cb_keep_private_tags.setEnabled(arg__1)
        self.dict_file_widget.setEnabled(arg__1)
        self.button_fix_output_dir.setEnabled(arg__1)
        self.output_folder.setEnabled(arg__1)

    def setDisabled(self, arg__1: bool):
        self.line_tag_actions.setDisabled(arg__1)
        self.cb_keep_private_tags.setDisabled(arg__1)
        self.dict_file_widget.setDisabled(arg__1)
        self.button_fix_output_dir.setDisabled(arg__1)
        self.output_folder.setDisabled(arg__1)

    @property
    def widget(self):
        return self.container_box


class FileSelector(QWidget):
    def __init__(self,
                 parent=None,
                 label: str = None,
                 button_label: str = '...',
                 button_action = None,  # User defined function to execute with the result returned by the dialog
                 directory: bool = False,
                 multiple_files: bool = False,
                 selection_filter: str = None,
                 freeze_user_selection: bool = False,   # Freeze the path after user selection. Prevent changes from external src.
                 ):
        super().__init__(parent=parent)
        self.button = QPushButton(button_label)
        self.button_action = button_action
        self.text_box = QLineEdit()
        self.text_box.setReadOnly(True)

        self.only_files = not directory
        self.filter = selection_filter if not directory else None
        self.multiple_files = multiple_files if not directory else False
        self.selection = None

        self.freeze_user_selection = freeze_user_selection
        self.__manual_selection = False

        self.button.clicked.connect(self.__selection_dialog)

        layout = QHBoxLayout()
        if label is not None:
            label = QLabel(label)
            layout.addWidget(label)
        layout.addWidget(self.text_box)
        layout.addWidget(self.button)
        self.setLayout(layout)

    def __selection_dialog(self):
        dlg = QFileDialog()
        if self.only_files:
            dlg.setFileMode(QFileDialog.AnyFile)
            if self.filter:
                dlg.setNameFilter(self.filter)
                dlg.selectNameFilter(self.filter)
        else:
            dlg.setFileMode(QFileDialog.DirectoryOnly)

        if dlg.exec_():
            self.selection = dlg.selectedFiles()
            if self.button_action is not None:
                self.selection = [self.button_action(f) for f in self.selection]

            if not self.multiple_files:
                self.selection = self.selection[0]
                self._set_text_box(self.selection)
            else:
                self._set_text_box(', '.join(self.selection))
            self.__manual_selection = True and self.freeze_user_selection

    @property
    def user_selection(self) -> (str, list):
        return self.selection

    def _set_text_box(self, new_text):
        if not self.__manual_selection:
            self.text_box.setText(new_text)

    def setDisabled(self, arg__1: bool):
        self.text_box.setDisabled(arg__1)
        self.button.setDisabled(arg__1)

    def setEnabled(self, arg__1: bool):
        self.text_box.setEnabled(arg__1)
        self.button.setEnabled(arg__1)


class SelectorWidget:
    def __init__(self):
        self.file_system_model = QFileSystemModel()

        self.file_list_view = QListView()
        self.file_list_view.setModel(self.file_system_model)
        self.file_list_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_list_view.doubleClicked.connect(self.__slot_go_in_directory)

        self.find_directory = FileSelector(button_label='Find folder',
                                           directory=True)
        self.find_directory.text_box.textChanged.connect(self.__update_list_view)

        self.button_up = QToolButton()
        print('--QIcon path: ' + os.path.join(ROOT_PATH, 'images/up.png'))
        button_up_icon = QIcon()
        button_up_icon.addPixmap(QPixmap(os.path.join(ROOT_PATH, 'images/up.png')), QIcon.Normal, QIcon.On)
        self.button_up.setIconSize(QSize(30, 30))
        self.button_up.setIcon(button_up_icon)
        self.button_up.clicked.connect(self.__one_level_up)

        self.cb_hold_selection = QCheckBox('Hold selection')
        self.cb_hold_selection.setChecked(False)
        self.cb_hold_selection.clicked.connect(self.__change_selection_mode)

        self.selection_table = SelectionTable()
        self.button_transfer_to_table = QPushButton('Add selection >>')
        self.button_transfer_to_table.clicked.connect(self.__add_selection_to_table)

        self.user_defined_output = False

        self.__file_layout = None

        self.build_layouts()

    def build_layouts(self):
        self.__file_layout = QGridLayout()
        self.__file_layout.addWidget(self.find_directory.text_box, 0, 0)
        self.__file_layout.addWidget(self.find_directory.button, 0, 1)
        self.__file_layout.addWidget(self.file_list_view, 1, 0)

        self.__nav_layout = QVBoxLayout()
        self.__nav_widget = QWidget()
        for w in [self.button_up, self.cb_hold_selection, self.button_transfer_to_table]:
            h_layout = QHBoxLayout()
            h_layout.addStretch()
            h_layout.addWidget(w)
            h_layout.addStretch()
            self.__nav_layout.addLayout(h_layout)

        self.__nav_widget.setLayout(self.__nav_layout)
        self.__nav_widget.setFixedWidth(150)
        self.__file_layout.addWidget(self.__nav_widget, 1, 1)

    def __change_selection_mode(self):
        self.file_list_view.clearSelection()
        if self.cb_hold_selection.isChecked():
            self.file_list_view.setSelectionMode(QAbstractItemView.MultiSelection)
        else:
            self.file_list_view.setSelectionMode(QAbstractItemView.ExtendedSelection)

    @property
    def file_explorer_layout(self):
        return self.__file_layout

    def __update_list_view(self):
        location = self.find_directory.text_box.text()
        self.file_list_view.setRootIndex(self.file_system_model.setRootPath(location))

    def __add_selection_to_table(self):
        if len(self.file_list_view.selectionModel().selectedIndexes()):
            for idx in self.file_list_view.selectionModel().selectedIndexes():
                self.selection_table.add_entry(self.file_system_model.filePath(idx))
        else:
            if self.find_directory.text_box.text() != '':
                self.selection_table.add_entry(self.find_directory.text_box.text())

    def go_in_directory(self, dir_path: str = None):
        if os.path.isdir(dir_path):
            self.file_list_view.setRootIndex(self.file_system_model.setRootPath(dir_path))
            self.find_directory._set_text_box(dir_path)

    def __slot_go_in_directory(self):
        idx = self.file_list_view.currentIndex()
        dir_path = self.file_system_model.filePath(idx)
        self.go_in_directory(dir_path)

    def __one_level_up(self):
        current_dir = self.find_directory.text_box.text()
        if current_dir != os.path.dirname(current_dir):
            # we are not at root level
            self.go_in_directory(os.path.dirname(current_dir))


class SelectionTable:
    def __init__(self, custom_cell_styler=None):
        self.table = QTableWidget()
        self.__initialize_table(custom_cell_styler)

        self.button_clear = QPushButton('Clear list')
        self.button_clear.clicked.connect(self.clear_table)

        self.button_clear_selection = QPushButton('Clear selection')
        self.button_clear_selection.clicked.connect(self.clear_selection)

        self.button_clear_invalid = QPushButton('Clear invalid')
        self.button_clear_invalid.clicked.connect(self.clear_invalid)

        self.__container = QVBoxLayout()
        h_box = QHBoxLayout()
        h_box.addWidget(self.button_clear_selection)
        h_box.addWidget(self.button_clear)
        h_box.addWidget(self.button_clear_invalid)
        h_box.addStretch()
        self.__container.addLayout(h_box)
        self.__container.addWidget(self.table)

        self.__rows_counter = 0
        self.__id_dict = dict()

    def __initialize_table(self, cell_style=None):
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderItem(0, QTableWidgetItem('Path'))
        self.table.setHorizontalHeaderItem(1, QTableWidgetItem('Valid'))
        self.table.setColumnHidden(1, True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setMinimumHeight(300)
        self.table.setMinimumWidth(400)
        if cell_style is not None:
            self.table.setItemDelegateForColumn(0, cell_style)      # Place ellipsis to the left of the text

    def add_entry(self, new_path):
        if not self.__is_duplicated(new_path):
            self.table.insertRow(self.__rows_counter)
            valid = self.__check_path_validity(new_path)
            self.table.setItem(self.__rows_counter, 0, QTableWidgetItem(new_path))
            self.table.setItem(self.__rows_counter, 1, QTableWidgetItem(str(valid)))
            if not valid:
                self.__change_row_colour(self.__rows_counter)
            self.__id_dict[new_path] = self.__rows_counter
            self.__rows_counter += 1
        else:
            warnings.warn('Duplicated entry: ' + new_path)

    @staticmethod
    def __check_path_validity(query):
        if os.path.isdir(query):
            files = [f for f in os.listdir(query) if f.endswith('.dcm')]
            valid = bool(len(files))
        elif os.path.isfile(query):
            valid = os.path.split(query)[-1].split('.')[-1].lower() == 'dcm'
        else:
            raise ValueError('Something went wrong. Got: ' + query)
        return valid

    def remove_entry(self, entry_path):
        row_to_remove = self.__id_dict[entry_path]
        self.table.removeRow(row_to_remove)
        self.__rows_counter -= 1

    def get_data(self, clear: bool=True) -> list:
        data = list()
        for r in range(self.__rows_counter):
            path, valid = self.table.item(r, 0), self.table.item(r, 1)
            data.append((path.text(), eval(valid.text())))
        if clear:
            self.clear_table()
        return data

    def __change_row_colour(self, row, colour=(255, 128, 128, 255)):
        for c in range(self.table.columnCount()):
            self.table.item(row, c).setBackground(QColor(*colour))

    def __is_duplicated(self, query):
        ret_val = False
        for r in range(self.table.rowCount()):
            ret_val = query == self.table.item(r, 0).text()
            if ret_val:
                break
        return ret_val

    def clear_table(self):
        self.table.clearContents()
        for r in range(self.__rows_counter):
            self.table.removeRow(r)
        self.__rows_counter = 0
        self.__id_dict = dict()

    def clear_invalid(self):
        num_removed = 0
        for r in range(self.__rows_counter).__reversed__():
            if not eval(self.table.item(r, 1).text()):
                self.table.removeRow(r)
                num_removed += 1
        self.__rows_counter -= num_removed

    def clear_selection(self):
        selection_idxs = self.table.selectionModel().selectedIndexes()
        for idx in selection_idxs:
            self.table.removeRow(idx.row())
        self.__rows_counter -= len(selection_idxs)
        return

    @property
    def container(self):
        return self.__container


class AnonymizerGUI:
    def __init__(self, parent=None):
        self.__file_selector_widget = SelectorWidget()
        self.__options_widget = OptionsWidget()

        self.__run_button = QPushButton('Run')
        self.__run_button.setStyleSheet("background-color: rgb(128, 255, 128);")
        self.__run_button.clicked.connect(self.__slot_run_button)
        self.__run_button.setDisabled(True)

        self.__file_selector_widget.selection_table.button_clear_selection.clicked.connect(self.__toggle_run_button)
        self.__file_selector_widget.selection_table.button_clear.clicked.connect(self.__toggle_run_button)
        self.__file_selector_widget.selection_table.button_clear_invalid.clicked.connect(self.__toggle_run_button)
        self.__file_selector_widget.button_transfer_to_table.clicked.connect(self.__toggle_run_button)

        self.layout = QGridLayout()

        self.build_gui()

    def build_gui(self):
        label_options = QLabel('Options')
        label_file_explorer = QLabel('Select a DICOM file or folder with DICOM files:')
        self.layout.addWidget(label_file_explorer, 0, 0)
        self.layout.addLayout(self.__file_selector_widget.file_explorer_layout, 1, 0)
        self.layout.addWidget(self.__run_button, 2, 0, 1, 2)
        self.layout.addWidget(label_options, 0, 1)
        v_box = QVBoxLayout()
        v_box.addWidget(self.__options_widget.widget)
        v_box.addLayout(self.__file_selector_widget.selection_table.container)
        self.layout.addLayout(v_box, 1, 1)
        #self.layout.addWidget(self.__file_selector_widget.run_button, 2, 0, 1, 2)

    def __toggle_run_button(self):
        if self.__file_selector_widget.selection_table.table.rowCount():
            self.__run_button.setEnabled(True)
        else:
            self.__run_button.setDisabled(True)

    def __slot_run_button(self):
        selected_data = self.__file_selector_widget.selection_table.get_data()
        paths_to_process = list()

        output_folder = ROOT_PATH if self.__options_widget.output_folder.text_box.text() == '' else self.__options_widget.output_folder.text_box.text()
        output_folder = os.path.join(output_folder, 'Anonymized_{}'.format(datetime.now().strftime('%H%M%S_%d%m%Y')))
        new_id = 0
        for (p, valid) in selected_data:
            if valid:
                if os.path.isdir(p):
                    # TODO: use walk to traverse the patient folder and gather all the studies. Up to 3 levels!
                    new_folder_name = 'Anonymized_{:04d}'.format(new_id)
                    files_in_path = [f for f in os.listdir(p) if f.endswith('.dcm')]
                    if len(files_in_path):
                        os.makedirs(os.path.join(output_folder, new_folder_name), exist_ok=True)
                        files_in_path.sort()
                        for i, f in enumerate(files_in_path):
                            new_f = os.path.join(output_folder, new_folder_name, 'Image_{:04d}.dcm'.format(i))
                            paths_to_process.append((os.path.join(p, f), new_f))
                elif os.path.isfile(p):
                    folder_path, file_name = os.path.split(p)
                    new_folder_path = os.path.join(output_folder, 'Anonymized_{:04d}'.format(new_id))
                    os.makedirs(new_folder_path, exist_ok=True)
                    paths_to_process.append((p, os.path.join(new_folder_path, 'Image_{:04d}'.format(new_id) + '.dcm')))
                new_id += 1

        tags = self.__options_widget.line_tag_actions.text()
        tags = tags.split(';') if tags != '' else list()     # Empty list
        tags = list(zip(*(iter(tags),) * 2))  # TODO: improve tag actions GUI [["tags", action], ["tags", action], ...]
        anonymization_rules = self.__get_anonymization_rules(tags, self.__options_widget.dict_file_widget.text_box.text())

        self.setDisabled(True)
        progress_increment = 100 / len(paths_to_process)
        dialog_progress = QProgressDialog('Processing files', 'Cancel', 0, 100)
        dialog_progress.setWindowModality(Qt.WindowModal)

        for i, (in_file, out_file) in enumerate(paths_to_process):
            self.run_anonymization(in_file, out_file,
                                   not self.__options_widget.cb_keep_private_tags.isChecked(),
                                   anonymization_rules)
            dialog_progress.setValue(progress_increment * i)
            if dialog_progress.wasCanceled():
                break
        dialog_progress.setValue(100)
        dialog_progress.close()

        info_dialog = QMessageBox()
        button_open_out_dir = QPushButton('Open output folder')
        info_dialog.setText('Output can be found in: '+output_folder)
        info_dialog.setStandardButtons(QMessageBox.Ok)
        info_dialog.addButton(button_open_out_dir, QMessageBox.NoRole)
        info_dialog.setIcon(QMessageBox.Information)
        info_dialog.exec_()
        if info_dialog.clickedButton() == button_open_out_dir:
            QDesktopServices.openUrl(QUrl.fromLocalFile(output_folder))

        self.setEnabled(True)

    @staticmethod
    def __get_anonymization_rules(tag: list=None, dictionary_file: str=None):
        # Create a new actions' dictionary from parameters in the GUI
        new_anonymization_rules = {}
        cpt = 0
        if tag:
            number_of_new_tags_actions = len(tag)
            if number_of_new_tags_actions > 0:
                for i in range(number_of_new_tags_actions):
                    current_tag_parameters = tag[i]

                    nb_parameters = len(current_tag_parameters)
                    if nb_parameters == 0:
                        continue

                    options = None
                    action_name = current_tag_parameters[1]

                    # Means that we are in regexp mode
                    if nb_parameters == 4:
                        options = {
                            "find": current_tag_parameters[2],
                            "replace": current_tag_parameters[3]
                        }

                    tags_list = [ast.literal_eval(current_tag_parameters[0])]

                    action = actions_map_name_functions[action_name]
                    # When generate_actions is called and we have options, we don't want use regexp
                    # as an action but we want to call it to generate a new method
                    if options is not None:
                        action = action_name

                    if cpt == 0:
                        new_anonymization_rules = generate_actions(tags_list, action, options)
                    else:
                        new_anonymization_rules.update(generate_actions(tags_list, action, options))
                    cpt += 1

        # Read an existing dictionary
        if dictionary_file:
            with open(dictionary_file) as json_file:
                data = json.load(json_file)
                for key, value in data.items():
                    action_name = value
                    options = None
                    if type(value) is dict:
                        action_name = value['action']
                        options = {
                            "find": value['find'],
                            "replace": value['replace']
                        }

                    l = [ast.literal_eval(key)]
                    action = eval(action_name)
                    if cpt == 0:
                        new_anonymization_rules = generate_actions(l, action, options)
                    else:
                        new_anonymization_rules.update(generate_actions(l, action, options))
                    cpt += 1

        return new_anonymization_rules

    @staticmethod
    def run_anonymization(input_file, output_file, delete_private_tags, anonymization_rules):
        # Launch the anonymization
        anonymize_dicom_file(input_file, output_file, anonymization_rules, delete_private_tags)

    def setDisabled(self, arg__1):
        self.__run_button.setDisabled(arg__1)
        self.__file_selector_widget.find_directory.setDisabled(arg__1)
        self.__options_widget.output_folder.setDisabled(arg__1)

    def setEnabled(self, arg__1):
        self.__run_button.setEnabled(arg__1)
        self.__file_selector_widget.find_directory.setEnabled(arg__1)
        self.__options_widget.output_folder.setEnabled(arg__1)


def main():
    app = QApplication([])      # THIS MUST BE THE FIRST INSTRUCTION!!!!
    app.setWindowIcon(QIcon(os.path.join(ROOT_PATH, 'images', 'app_icon_128.png')))
    window = QWidget()

    gui = AnonymizerGUI()

    # Applicaton setup
    window.setWindowTitle('DICOM Anonymizer')
    window.setGeometry(300, 300, 800, 400)
    window.setLayout(gui.layout)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
