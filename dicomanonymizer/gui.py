from PySide2.QtWidgets import QApplication, QLabel, QWidget, QCheckBox, QLineEdit, QFileSystemModel, QPushButton, QTreeView, QGroupBox, QFileDialog, QFormLayout, QListView
from PySide2.QtWidgets import QGridLayout, QVBoxLayout, QHBoxLayout, QToolButton
from PySide2.QtCore import Qt, QDir, QSize
from PySide2.QtGui import QIcon, QPixmap

import os, sys
import ast

from dicomanonymizer.anonymizer import anonymize, generate_actions
import json


class UserParameters:
    def __init__(self,
                 input_path: str = '',
                 output_path: str = '',
                 tag: list = None,
                 dictionary_file: str = None,
                 keep_private_tags: bool = False):
        self.tag = tag
        self.input_path = input_path
        self.output_path = output_path
        self.tag = tag
        self.dictionary_file = dictionary_file
        self.keep_private_tags = keep_private_tags


def build_options_widget():
    # Options
    cb_keep_private_tags = QCheckBox("Keep Private Tags")
    label_tag_actions = QLabel('Tag actions')
    line_tag_actions = QLineEdit()
    dict_file_widget = FileSelector(label='Dictionary', button_label='...', selection_filter='JSON (*.json)')

    # Options layouts
    layout_tag_actions = QHBoxLayout()
    layout_tag_actions.addWidget(label_tag_actions)
    layout_tag_actions.addWidget(line_tag_actions)

    layout_options = QVBoxLayout()
    layout_options.alignment()
    layout_options.addWidget(cb_keep_private_tags)
    layout_options.addLayout(layout_tag_actions)
    layout_options.addWidget(dict_file_widget)
    layout_options.setAlignment(Qt.AlignTop)
    groupbox_options = QGroupBox()
    groupbox_options.setLayout(layout_options)
    return groupbox_options


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


class FileExplorer:
    def __init__(self, output_suffix: str = '__Anonymized'):
        self.file_system_model = QFileSystemModel()
        # self.file_system_model.setRootPath(QDir.rootPath())

        self.file_list_view = QListView()
        self.file_list_view.setModel(self.file_system_model)
        self.file_list_view.clicked.connect(self.update_selection)
        self.file_list_view.doubleClicked.connect(self.__slot_go_in_directory)

        self.find_directory = FileSelector(button_label='Select folder',
                                           directory=True)
        self.find_directory.text_box.textChanged.connect(self.__update_list_view)

        self.button_up = QToolButton()
        button_up_icon = QIcon()
        button_up_icon.addPixmap(QPixmap('./images/up.png'), QIcon.Normal, QIcon.On)
        self.button_up.setIconSize(QSize(30, 30))
        self.button_up.setIcon(button_up_icon)
        self.button_up.clicked.connect(self.__one_level_up)

        self.run_button = QPushButton('Run')

        self.selection = QLineEdit(os.getcwd())
        self.selection.setReadOnly(True)

        self.__output_suffix = output_suffix
        self.output_path = FileSelector(button_label='Change output folder',
                                        directory=True,
                                        button_action=self.__add_suffix,
                                        freeze_user_selection=True)

        self.user_defined_output = False

        self.__info_layout = None
        self.__file_layout = None

        self.build_layouts()

    def build_layouts(self):
        self.__info_layout = QGridLayout()
        self.__info_layout.addWidget(self.selection, 0, 0)
        self.__info_layout.addWidget(self.output_path.text_box, 1, 0)
        self.__info_layout.addWidget(self.run_button, 0, 1)
        self.__info_layout.addWidget(self.output_path.button, 1, 1)

        self.__file_layout = QGridLayout()
        self.__file_layout.addWidget(self.find_directory.text_box, 0, 0)
        self.__file_layout.addWidget(self.find_directory.button, 0, 1)
        self.__file_layout.addWidget(self.file_list_view, 1, 0)

        self.__nav_layout = QVBoxLayout()
        self.__nav_layout.addWidget(self.button_up)
        self.__nav_layout.setAlignment(Qt.AlignTop)
        self.__file_layout.addLayout(self.__nav_layout, 1, 1)

    @property
    def file_explorer_layout(self):
        return self.__file_layout

    @property
    def information_layout(self):
        return self.__info_layout

    def set_run_button_callback(self, callback_fnc):
        self.run_button.clicked.connect(callback_fnc)

    def __add_suffix(self, in_path: str):
        return in_path + self.__output_suffix

    def __update_list_view(self):
        location = self.find_directory.text_box.text()
        self.file_list_view.setRootIndex(self.file_system_model.setRootPath(location))

    def update_selection(self):
        idx = self.file_list_view.currentIndex()
        self.selection.setText(self.file_system_model.filePath(idx))

        if not self.user_defined_output:
            folder_name = '_Anonymyzed'
            dir_path, old_name = os.path.split(self.selection.text())
            if os.path.isdir(self.selection.text()):
                folder_name = old_name + folder_name
            else:
                folder_name = old_name.split('.')[0] + folder_name
            self.output_path._set_text_box(os.path.join(dir_path, folder_name))

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


def run_anonymizer(user_parameters: UserParameters):
    # Create a new actions' dictionary from parameters in the GUI
    new_anonymization_actions = {}
    cpt = 0
    if user_parameters.tag:
        number_of_new_tags_actions = len(user_parameters.tag)
        if number_of_new_tags_actions > 0:
            for i in range(number_of_new_tags_actions):
                current_tag_parameters = user_parameters.tag[i]

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

                action = eval(action_name)
                # When generate_actions is called and we have options, we don't want use regexp
                # as an action but we want to call it to generate a new method
                if options is not None:
                    action = action_name

                if cpt == 0:
                    new_anonymization_actions = generate_actions(tags_list, action, options)
                else:
                    new_anonymization_actions.update(generate_actions(tags_list, action, options))
                cpt += 1

    # Read an existing dictionary
    if user_parameters.dictionary_file:
        with open(user_parameters.dictionary_file) as json_file:
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
                action = defined_action_map[action_name] if action_name in defined_action_map else eval(action_name)
                if cpt == 0:
                    new_anonymization_actions = generate_actions(l, action, options)
                else:
                    new_anonymization_actions.update(generate_actions(l, action, options))
                cpt += 1

    # Launch the anonymization
    anonymize(user_parameters.input_path, user_parameters.output_path, new_anonymization_actions, not user_parameters.keep_private_tags)


if __name__ == "__main__":
    app = QApplication([])      # THIS MUST BE THE FIRST INSTRUCTION!!!!
    window = QWidget()

    options_widget = build_options_widget()

    file_explorer = FileExplorer()

    # App layout
    app_layout = QGridLayout()
    label_options = QLabel('Options')
    label_file_explorer = QLabel('Select a DICOM file or folder with DICOM files:')
    app_layout.addWidget(label_file_explorer, 0, 0)
    app_layout.addLayout(file_explorer.file_explorer_layout, 1, 0)
    app_layout.addLayout(file_explorer.information_layout, 2, 0, 1, 2)
    app_layout.addWidget(label_options, 0, 1)
    app_layout.addWidget(options_widget, 1, 1)

    # Applicaton setup
    window.setWindowTitle('DICOM Anonymizer')
    window.setGeometry(300, 300, 800, 400)
    window.setLayout(app_layout)
    window.show()
    sys.exit(app.exec_())
