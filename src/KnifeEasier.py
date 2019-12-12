#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os, sys, time, shutil, json

from PySide.QtGui import *
from PySide.QtCore import *

from qsshelper import QSSHelper
from KnifeConfHandler import *
from KnifeRequest import *


CONF_JSON = os.path.join("conf", "config.js")
KEY_MODULES = "modules"
KEY_CRENDENTIAL = "crendential"
SELECT_MODULE_TIP = "<select module>"

DIR_USER_CONF = "user_conf"
DIR_KNIFE_APP = "C_Application"
DIR_KNIFE_OAM = os.path.join(DIR_KNIFE_APP, "SC_OAM", "Target")
KNIFE_NAME = "knife"
ZIP_FORMAT = "zip"

MSG_NO_MODULE = "Oppos! No selected module!"
MSG_NO_FILE = "Opoos! No selected files!"
MSG_LOCAL_KNIFE = "No Knife-Dir provided, knife.zip will be saved in local PC."
MSG_GET_KNIFE = "Get knife.zip from:"
MSG_CREATED_KNIFE = "Send request successfully, see details from:"

HOVER_SUFFIX = "_hover"

KEY_BASELINE = "knife_request[baseline]"
KEY_HW_MODULE = "knife_request[module]"

KEY_KNIFE_DIR = "knife_request[knife_dir]"
KEY_FORCE_KNIFE_DIR = "knife_request[force_knife_dir]"
KEY_CHANGE_COMPONENT = "change_components"
KEY_EXPECTED_RESULT = "knife_request[flags][]"
KEY_SC = "knife_request[rebuild_sc][]"
KEY_REF_ID = "knife_request[reference_id]"
KEY_NO_REF = "knife_request[no_reference]"
KEY_PURPOSE ="knife_request[purpose]"
KEY_RECIPIENTS = "knife_request[recipients_list]_values[]"

PKG_RESULTS = ["StandarBTS package (BTSSM)", "Test packages"]
HW_MODULE_DISP = ["FSM-r3", "FSM-r4", "COMMON FDD build (frozen FSM-r2 + FSM-r3 + AirScale)"]
PURPOSE_TYPE = ["debug", "correction", "other"]


class KnifeUI(QMainWindow):

    def __init__(self):
        super(KnifeUI, self).__init__()
        self.localToKnife = dict()
        self.module_list = list()
        self.results_list = list()
        with open(CONF_JSON) as fp:
            conf_json = json.load(fp)
            self.module_list = conf_json.get(KEY_MODULES, None)
            self.user, self.passwd = conf_json.get(KEY_CRENDENTIAL, [None, None])

        if self.user is None or self.passwd is None:
            self.getCrendential()

        self.dataAgent = KnifeConfHandler()
        self.requestAgent = self.getRequestAgent()
        self.initUI()
        self.fileSearchPath = QDir.homePath()
        self.confPath = DIR_USER_CONF

    def getRequestAgent(self):
        max_retry = 2
        while(True):
            if self.user is None or self.passwd is None:
                self.getCrendential()
            try:
                return WftHttpsClient(self.user, self.passwd)
            except ReqError as e:
                if e.err == 301:
                    self.getCrendential(inValid=True)
                else:
                    raise Exception(e.msg)
            except Exception as e:
                raise e


    def getCrendential(self, inValid=False):
        self.user, self.passwd, ok = CrendetialDialog(inValid=inValid).exec_()
        if not ok:
            sys.exit(0)

        with open(CONF_JSON) as fp:
            conf_json = json.load(fp)
        with open(CONF_JSON, 'w') as fp:
            conf_json[KEY_CRENDENTIAL] = [self.user, self.passwd]
            json.dump(conf_json, fp)

    def initUI(self):
        # ---------------1. tap widget-------------------
        self.showWidget = QStackedWidget()
        self.showWidget.addWidget(self.initPackagePage())
        self.showWidget.addWidget(self.initRequestPage())

        #----------------2. left toolBar---------------
        self.pageSelector = PageSelector(self.showWidget)
        self.pageSelector.addHoverAction("images/package.png", "images/package_hover.png", "Package", 0)
        self.pageSelector.addHoverAction("images/request.png", "images/request_hover.png", "Request", 1)

        #----------------3. main Layout------------------
        mainWidget = QWidget()
        mainLayout = QHBoxLayout()
        mainLayout.addWidget(self.pageSelector)
        mainLayout.addWidget(self.showWidget)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(0)
        mainWidget.setLayout(mainLayout)

        #----------------4. status bar(progress bar)------------------
        self.pgrBar = QProgressBar()
        self.statusBar().addWidget(self.pgrBar, 2)
        self.statusBar().setSizeGripEnabled(False)
        self.statusBar().hide()

        #----------------5. set window-------------------
        qss = QSSHelper.open_qss(os.path.join('qss/knife_ui.qss'))
        screen = QDesktopWidget().screenGeometry()
        self.setStyleSheet(qss)
        self.setCentralWidget(mainWidget)
        self.setFixedSize(500, 430)
        size =  self.geometry()
        self.move((screen.width()-size.width())/2, (screen.height()-size.height())/2)
        self.setWindowIcon(QIcon("images/bug.png"))
        self.setWindowTitle('KnifeEasier version 1.1')
        self.moduleComboBox.clearFocus()
        self.show()

    def initPackagePage(self):
        # module selection
        self.moduleComboBox = QComboBox()
        self.moduleComboBox.addItems(self.module_list)
        self.moduleComboBox.setEditable(True)
        self.moduleComboBox.setCurrentIndex(-1)
        self.moduleComboBox.lineEdit().setPlaceholderText(SELECT_MODULE_TIP)

        # file selection
        self.fileTableWidget = QTableWidget()
        self.fileTableWidget.setColumnCount(1)
        self.fileTableWidget.setGridStyle(Qt.NoPen)
        self.fileTableWidget.setColumnWidth(0, 300)
        self.fileTableWidget.verticalHeader().setVisible(False)
        self.fileTableWidget.horizontalHeader().setVisible(False)
        self.fileTableWidget.setSelectionBehavior(QAbstractItemView.SelectRows)

        # add/del/compress button
        addBtn = HoverButton("images/add.png", tip="add patch files", receiver=self.openFileDialog)
        delBtn = HoverButton("images/delete.png", tip="delete items", receiver=self.deleteFileItem)
        zipBtn = HoverButton("images/compress.png", tip="create knife.zip", receiver=self.startCreateKnife)
        self.fileToolWidget = ToolWidget(addBtn, delBtn, zipBtn)

        # package page layout
        self.packagePage = QWidget()
        pkgLayout = QVBoxLayout()
        pkgLayout.addWidget(self.moduleComboBox)
        pkgLayout.addWidget(self.fileTableWidget)
        pkgLayout.addWidget(self.fileToolWidget)
        pkgLayout.setContentsMargins(11, 11, 11, 0)
        self.packagePage.setLayout(pkgLayout)
        return self.packagePage

    def initRequestPage(self):
        # knife configuration
        self.baselineEdit = BaseLineEdit(self)
        self.hwModuleComboBox = ComboBoxUpdateTip(HW_MODULE_DISP)
        self.knifeDirEdit = QLineEdit()
        self.changeBuildConfCheckBox = QCheckBox("Modify build configuration")
        kcLayout = QFormLayout()
        kcLayout.addRow("Baseline:", self.baselineEdit)
        kcLayout.addRow("Module:", self.hwModuleComboBox)
        kcLayout.addRow("Knife package path:", self.knifeDirEdit)
        kcLayout.addRow(self.changeBuildConfCheckBox)
        self.knifeConfGroup = QGroupBox("Knife Configuration")
        self.knifeConfGroup.setLayout(kcLayout)

        # Expected results
        self.expectedResultCheckBoxs = list()
        erLayout = QVBoxLayout()
        for result in PKG_RESULTS:
            resultCheckBox = QCheckBox(result)
            erLayout.addWidget(resultCheckBox)
            self.expectedResultCheckBoxs.append(resultCheckBox)
        self.expectedResultsGroup = QGroupBox("Expected Results")
        self.expectedResultsGroup.setLayout(erLayout)

        # Addtional Info
        self.refEdit = ReferenceEdit(self)
        self.noRefCheckBox = CheckBoxWithFontSize("No Reference", 11)
        self.purposeComboBox = ComboBoxUpdateTip(PURPOSE_TYPE)
        self.recipientsEdit = QLineEdit()
        aiLayout = QFormLayout()
        aiLayout.addRow("Reference:", self.refEdit)
        aiLayout.addRow(" ", self.noRefCheckBox)
        aiLayout.addRow("Purpose:", self.purposeComboBox)
        aiLayout.addRow("Recipients List:", self.recipientsEdit)
        self.addInfoGroup = QGroupBox("Addtional Info")
        self.addInfoGroup.setLayout(aiLayout)

        # import/export/request buttion
        importBtn = HoverButton("images/import.png", tip="Import exsited config", receiver=self.importConfFile)
        exportBtn = HoverButton("images/export.png", tip="Export config to file", receiver=self.exportConfFile)
        requestBtn = HoverButton("images/create.png", tip="create new knife request", receiver=self.sendRequset)
        confToolWidget = ToolWidget(importBtn, exportBtn, requestBtn)

        self.requestPage = QWidget()
        requestLayout = QVBoxLayout()
        requestLayout.addWidget(self.knifeConfGroup)
        requestLayout.addWidget(self.expectedResultsGroup)
        requestLayout.addWidget(self.addInfoGroup)
        requestLayout.addWidget(confToolWidget, 0, Qt.AlignBottom)
        self.requestPage.setLayout(requestLayout)

        return self.requestPage

    def showProgress(self):
        self.statusBar().show()
        self.setFixedSize(500, 450)

    def hideProgress(self):
        self.statusBar().hide()
        self.setFixedSize(500, 430)

    def switchRefEdit(self, isChecked):
        self.refEdit.setDisabled(isChecked)

    def resizeEvent(self, event):
        self.fileTableWidget.setColumnWidth(0, self.fileTableWidget.width())

    def openFileDialog(self):
        files, _ = QFileDialog.getOpenFileNames(self, 'Open File', self.fileSearchPath)
        if files:
            self.fileSearchPath = os.path.dirname(files[0])
        for fileFullPath in files:
            if fileFullPath in self.localToKnife:
                continue
            fileWidget = CellWidget(os.path.basename(fileFullPath), fileFullPath, self.localToKnife)
            self.fileTableWidget.setRowCount(self.fileTableWidget.rowCount()+1)
            self.fileTableWidget.setCellWidget(self.fileTableWidget.rowCount()-1, 0, fileWidget)
            self.localToKnife[fileFullPath] = ""
        self.fileTableWidget.resizeRowsToContents()

    def deleteFileItem(self):
        for itemIndex in self.fileTableWidget.selectedIndexes():
            self.fileTableWidget.removeRow(itemIndex.row())

    def startCreateKnife(self):
        # No selected files
        if not self.localToKnife:
            MsgDialog(self, MSG_NO_FILE).exec_()
            return

        moduleName = self.moduleComboBox.currentText()
        if not moduleName:
            MsgDialog(self, MSG_NO_MODULE).exec_()
            return

        # Input knife dir in ROTTA
        remotePath, ok = InputDialog(self, "Knife-Dir in ROTTA:").exec_()
        if ok:
            self.showProgress()
            knifeDir = self.compressKnife(moduleName, remotePath)
            MsgDialog(self, normalMsg=MSG_GET_KNIFE, selectableMsg=knifeDir).exec_()
            self.hideProgress()

    def compressKnife(self, moduleName, remotePath=None):
        self.pgrBar.setValue(0)

        # archive knife.zip
        curTime = time.strftime('%Y%m%d_%H%M%S', time.gmtime())
        zipRoot = os.path.join("local_knifes", curTime)
        modulePath = os.path.join(zipRoot, DIR_KNIFE_OAM, moduleName)
        for fullPath in self.localToKnife:
            dstPath = os.path.join(modulePath, self.localToKnife[fullPath])
            if not os.path.exists(dstPath):
                os.makedirs(dstPath)
            shutil.copy2(fullPath, dstPath)
        self.pgrBar.setValue(40)

        zipName = os.path.join(zipRoot, "knife")
        shutil.make_archive(zipName, ZIP_FORMAT, root_dir=zipRoot, base_dir=DIR_KNIFE_APP)
        shutil.rmtree(os.path.join(zipRoot, DIR_KNIFE_APP))
        self.pgrBar.setValue(70)

        # copy to remote folder
        if remotePath:
            qdirRemotePath = os.path.join(remotePath, curTime)
            os.makedirs(qdirRemotePath)
            if not os.path.exists(qdirRemotePath):
                os.makedirs(qdirRemotePath)
            shutil.copy2("%s.%s" % (zipName, ZIP_FORMAT), qdirRemotePath)
            shutil.rmtree(zipRoot)
            self.pgrBar.setValue(100)
            self.knifeDirEdit.setText(qdirRemotePath)
            return qdirRemotePath
        else:
            self.pgrBar.setValue(100)
            MsgDialog(self, normalMsg=MSG_LOCAL_KNIFE, btnName="OK, I see.").exec_()
            return os.path.abspath(zipRoot)

    def showConf(self):
        self.baselineEdit.setText(self.dataAgent.getBaseline())
        hw_module = self.dataAgent.getHWModule()
        if hw_module.upper() == "COMMON":
            hw_module = "COMMON FDD build (frozen FSM-r2 + FSM-r3 + AirScale)"
        index = self.hwModuleComboBox.findText(hw_module)
        self.hwModuleComboBox.setCurrentIndex(index)
        self.knifeDirEdit.setText(self.dataAgent.getKnifeDir())
        self.changeBuildConfCheckBox.setChecked(self.dataAgent.getChangeBuildConf())

        expectedResults = self.dataAgent.getExpectedResult()
        for resultCheckBox in self.expectedResultCheckBoxs:
            if resultCheckBox.text() in expectedResults:
                resultCheckBox.setChecked(True)
            else:
                resultCheckBox.setChecked(False)

        self.refEdit.setText(self.dataAgent.getRefName())
        self.noRefCheckBox.setChecked(self.dataAgent.getNoRef())
        index = self.purposeComboBox.findText(self.dataAgent.getPurpose())
        self.purposeComboBox.setCurrentIndex(index)
        self.recipientsEdit.setText(self.dataAgent.getRecipients())

    def saveConfCache(self):
        self.dataAgent.setBaseline(self.baselineEdit.text())
        self.dataAgent.setHWModule(self.hwModuleComboBox.currentText())
        self.dataAgent.setKnifeDir(self.knifeDirEdit.text())
        self.dataAgent.setChangeBuildConf(self.changeBuildConfCheckBox.isChecked())

        for resultCheckBox in self.expectedResultCheckBoxs:
            if resultCheckBox.isChecked():
                self.dataAgent.setExpectedResult(resultCheckBox.text())

        self.dataAgent.setRefName(self.refEdit.text())
        self.dataAgent.setNoRef(self.noRefCheckBox.isChecked())
        self.dataAgent.setPurpose(self.purposeComboBox.currentText())
        self.dataAgent.setRecipients(self.recipientsEdit.text())

    def exportConfFile(self):
        fileName, _ = QFileDialog.getSaveFileName(self, "Export config", self.confPath)
        if fileName:
            self.saveConfCache()
            self.dataAgent.writeConf(fileName)
            self.confPath = os.path.dirname(fileName)

    def importConfFile(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Import config", self.confPath)
        if fileName:
            self.dataAgent.readConf(fileName)
            self.confPath = os.path.dirname(fileName)
            self.showConf()

    def validateParms(self):
        isValidBaseline = True
        isExistKnifeZip = True
        isValidReference = True
        hasAtLeastResult = False
        errReasonMsg = ""
        # checking baseline
        baseline = self.baselineEdit.text().strip()
        baseline_list = self.requestAgent.query_baseline(baseline)
        if len(baseline_list) == 0:
            errReasonMsg += "- No matched baseline.\n"
            isValidBaseline = False
        elif len(baseline_list) == 1:
            if baseline != baseline_list[0]:
                errReasonMsg += "- Not completely matched: %s\n" % baseline
                isValidBaseline = False
        elif len(baseline_list) >1:
            errReasonMsg += "- Multiple matched baseline.\n"
            isValidBaseline = False

        # checking if knife.zip exist
        knifeZipPath = os.path.join(self.knifeDirEdit.text().strip(), "knife.zip")
        if not os.path.isfile(knifeZipPath):
            errReasonMsg += "- No knife.zip found in knife dir.\n"
            isExistKnifeZip = False

        # checking reference
        if not self.noRefCheckBox.isChecked():
            curRefName = self.refEdit.text().strip()
            referenceDict = self.requestAgent.query_reference(curRefName)
            if len(referenceDict) == 0:
                errReasonMsg += "- No matched reference.\n"
                isValidReference = False
            elif len(referenceDict) == 1:
                for name, id in referenceDict.items():
                    self.refEdit.setText(name)
                    self.curRefID = id
            elif len(referenceDict) >1:
                if curRefName not in referenceDict:
                    errReasonMsg += "- Not specific reference.\n"
                    isValidReference = False
                else:
                    self.curRefID = referenceDict[curRefName]

        # checking expected results
        for resultCheckbox in self.expectedResultCheckBoxs:
            if resultCheckbox.isChecked():
                hasAtLeastResult = True
                break
        if not hasAtLeastResult:
            errReasonMsg += "- Select at least one expected result.\n"

        return (isValidBaseline and isValidReference and hasAtLeastResult), errReasonMsg

    def sendRequset(self):
        self.showProgress()
        self.pgrBar.setValue(0)

        # 1. valid parameter
        isValid, errMsg = self.validateParms()
        if not isValid:
            WarnDialog(self, normalMsg="Invalid request:", errMsg=errMsg[0:-1]).exec_()
            self.hideProgress()
            return
        else:
            self.pgrBar.setValue(30)

        # 2. convert parameter
        self.saveConfCache()
        knife_conf = self.dataAgent.converKnifeConf(self.curRefID)
        self.pgrBar.setValue(60)

        # 3. send request
        createdUrl = self.requestAgent.create_knife(knife_conf)
        self.pgrBar.setValue(100)

        MsgDialog(self, normalMsg=MSG_CREATED_KNIFE, selectableMsg=createdUrl).exec_()
        self.hideProgress()


class PageSelector(QToolBar):
    def __init__(self, stackedWidget):
        super(PageSelector, self).__init__()
        self.setOrientation(Qt.Vertical)
        self.setStyleSheet("QToolBar {background-color: rgb(60,60,60);border-top-color: rgb(130,130,130);} " \
                           "QToolBar > QToolButton:hover {background-color: black;}")
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.stackedWidget = stackedWidget
        self.actionInfo = dict()
        self.currentAction = None
        self.actionTriggered.connect(self.selectPage)

    def addHoverAction(self, image, hover_image, text, pageId):
        action = self.addAction(QIcon(image), text)
        self.actionInfo[action] = [image, hover_image, pageId]
        if self.currentAction is None:
            self.selectPage(action)

    def selectPage(self, action):
        if action == self.currentAction:
            return

        if self.currentAction is not None:
            image, hover_image, pageId = self.actionInfo[self.currentAction]
            self.currentAction.setIcon(QIcon(image))

        image, hover_image, pageId = self.actionInfo[action]
        action.setIcon(QIcon(hover_image))
        self.currentAction = action
        self.stackedWidget.setCurrentIndex(pageId)


class HoverButton(QToolButton):
    def __init__(self, image, text=None, tip=None, size=24, receiver=None):
        self.image = image
        self.hover_image = self.get_hover_image(image)

        super(HoverButton, self).__init__()
        self.setIcon(QIcon(self.image))
        self.setIconSize(QSize(size, size))
        if text:
            self.setText(text)
            self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        if tip:
            self.setToolTip(tip)
        if receiver:
            self.clicked.connect(receiver)

    @staticmethod
    def get_hover_image(image):
        image_name, suffix = os.path.splitext(image)
        return HOVER_SUFFIX.join([image_name, suffix])

    def enterEvent(self, event):
        self.setIcon(QIcon(self.hover_image))

    def leaveEvent(self, event):
        self.setIcon(QIcon(self.image))


class CheckBoxWithFontSize(QCheckBox):
    def __init__(self, text, fontSize):
        super(CheckBoxWithFontSize, self).__init__(text)
        self.setStyleSheet("QCheckBox {font-size: %spx;} QCheckBox::indicator{width: %spx; height: %spx;}" % \
                           (fontSize, fontSize, fontSize))


class ComboBoxUpdateTip(QComboBox):
    def __init__(self, items=None):
        super(ComboBoxUpdateTip, self).__init__()
        if items:
            self.addItems(items)
        self.currentIndexChanged[str].connect(self.changeToolTip)

    def changeToolTip(self, text):
        self.setToolTip(text)


class WarningLabel(QLabel):
    def __init__(self, text):
        super(WarningLabel, self).__init__(text)
        self.setStyleSheet("QLabel {font-size: 10px; color: red}")


class BaseLineEdit(QLineEdit):
    def __init__(self, parent):
        super(BaseLineEdit, self).__init__(parent)
        self.parent = parent
        self.returnPressed.connect(self.completeBaseline)

    def completeBaseline(self):
        self.parent.setDisabled(True)
        baselineList = self.parent.requestAgent.query_baseline(self.text().strip())
        if baselineList:
            completer = QCompleter(baselineList)
            completer.activated[str].connect(self.setText)
            self.setCompleter(completer)
            completer.complete()
        else:
            formLayout = self.parent.knifeConfGroup.layout()
            formLayout.insertRow(1, "", WarningLabel("   No result found"))
        self.parent.setEnabled(True)


class ReferenceEdit(QLineEdit):
    def __init__(self, parent):
        super(ReferenceEdit, self).__init__(parent)
        self.parent = parent
        self.setPlaceholderText("Fault or Feature")
        self.returnPressed.connect(self.completeRefID)

    def completeRefID(self):
        self.parent.setDisabled(True)
        self.parent.referenceDict = self.parent.requestAgent.query_reference(self.text().strip())
        if self.parent.referenceDict:
            completer = QCompleter(list(self.parent.referenceDict.keys()))
            completer.activated[str].connect(self.setText)
            self.setCompleter(completer)
            completer.complete()
        else:
            formLayout = self.parent.addInfoGroup.layout()
            formLayout.insertRow(1, "", WarningLabel("   No result found"))
        self.parent.setEnabled(True)


class MsgDialog(QDialog):
    def __init__(self, parent, normalMsg=None, selectableMsg=None, btnName=None):
        super(MsgDialog, self).__init__(parent)
        msgLayout = QVBoxLayout()
        self.setLayout(msgLayout)
        self.setWindowIcon(QIcon("images/idea-bulb.png"))
        self.setWindowTitle("Hmm~~")

        if normalMsg:
            normalLabel = QLabel(normalMsg)
            msgLayout.addWidget(normalLabel)
        if selectableMsg:
            selectableLabel = QLabel(selectableMsg)
            selectableLabel.setTextInteractionFlags(Qt.TextSelectableByMouse)
            selectableLabel.setStyleSheet("QLabel {font-weight: bold;}")
            msgLayout.addWidget(selectableLabel)
        if btnName:
            OKBtn = QPushButton(btnName)
            OKBtn.clicked.connect(self.close)
            msgLayout.addWidget(OKBtn)


class WarnDialog(QDialog):
    def __init__(self, parent, normalMsg=None, errMsg=None):
        super(WarnDialog, self).__init__(parent)
        msgLayout = QVBoxLayout()
        self.setLayout(msgLayout)
        self.setWindowIcon(QIcon("images/idea-bulb.png"))
        self.setWindowTitle("Oh, no!")

        if normalMsg:
            normalLabel = QLabel(normalMsg)
            msgLayout.addWidget(normalLabel)
        if errMsg:
            errLabel = QLabel(errMsg)
            errLabel.setTextInteractionFlags(Qt.TextSelectableByMouse)
            errLabel.setStyleSheet("QLabel {color: red;}")
            msgLayout.addWidget(errLabel)


class InputDialog(QDialog):
    def __init__(self, parent, label):
        super(InputDialog, self).__init__(parent)
        inputLayout = QGridLayout()
        self.setLayout(inputLayout)
        self.setWindowIcon(QIcon("images/idea-bulb.png"))
        self.setWindowTitle("Hmm~~")
        label = QLabel(label)
        self.edit = QLineEdit()
        OKBtn = QPushButton("OK")
        OKBtn.setStyleSheet("QPushButton:hover {color: #1afa29}")
        OKBtn.clicked.connect(self.accept)
        CancelBtn = QPushButton("Cancel")
        CancelBtn.setStyleSheet("QPushButton:hover {color: #ea9518}")
        CancelBtn.clicked.connect(self.reject)
        btnLayout = QHBoxLayout()
        btnLayout.addWidget(OKBtn)
        btnLayout.addWidget(CancelBtn)
        inputLayout.addWidget(label, 0, 0, alignment=Qt.AlignLeft)
        inputLayout.addWidget(self.edit, 1, 0)
        inputLayout.addLayout(btnLayout, 2, 0)

    def exec_(self):
        super(InputDialog, self).exec_()
        return self.edit.text(), (self.result() == QDialog.Accepted)

class CrendetialDialog(QDialog):
    def __init__(self, inValid=False):
        super(CrendetialDialog, self).__init__()
        qss = QSSHelper.open_qss(os.path.join('qss/knife_ui.qss'))
        self.setStyleSheet(qss)
        self.setWindowIcon(QIcon("images/idea-bulb.png"))
        self.setWindowTitle("Fill me! Fill me!")
        self.userEdit = QLineEdit()
        self.passwdEdit = QLineEdit()
        self.passwdEdit.setEchoMode(QLineEdit.Password)
        LoginBtn = QPushButton("Login")
        LoginBtn.setStyleSheet("QPushButton:hover {color: #1afa29}")
        LoginBtn.clicked.connect(self.accept)

        formLayout = QFormLayout()
        formLayout.addRow("User:", self.userEdit)
        formLayout.addRow("passwdEdit:", self.passwdEdit)
        if inValid:
            formLayout.addRow("", WarningLabel("Invalid user or passwd"))

        formLayout.addRow("", LoginBtn)
        self.setLayout(formLayout)

    def exec_(self):
        super(CrendetialDialog, self).exec_()
        return self.userEdit.text(), self.passwdEdit.text(), (self.result() == QDialog.Accepted)


class ToolWidget(QWidget):
    def __init__(self, firstBtn, secondBtn, thirdBtn):
        super(ToolWidget, self).__init__()

        leftToolBar = QToolBar()
        leftToolBar.addWidget(firstBtn)
        leftToolBar.addWidget(secondBtn)

        rightToolBar = QToolBar()
        rightToolBar.addSeparator()
        rightToolBar.addWidget(thirdBtn)

        toolLayout = QHBoxLayout()
        toolLayout.addWidget(leftToolBar, 0, Qt.AlignLeft)
        toolLayout.addWidget(rightToolBar, 0, Qt.AlignRight)
        toolLayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(toolLayout)
        #self.setStyleSheet("QWidget {border: 1px solid rgb(20,20,20); padding: 0px; margin: 0px;}")


class CellWidget(QWidget):
    def __init__(self, fileName, filePath, localToKnife):
        super(CellWidget, self).__init__()
        self.localToKnifeCopy = localToKnife
        self.fileFullPath = filePath

        # file icon
        fileIcon = QIcon(QFileIconProvider().icon(QFileInfo(filePath)))
        fileIconBtn = QToolButton()
        fileIconBtn.setIcon(fileIcon)
        fileIconBtn.setStyleSheet("QToolButton {background-color: transparent;}")

        # show file name
        fileNameLabel = QLabel(fileName)
        fileNameLabel.setToolTip(filePath)

        # Edit path in knife
        pathStyleSheet = '''
        QLineEdit
        {
          background-color: transparent;
          border: 0px solid rgb(20,20,20);
          color: rgb(110,110,110);
          selection-background-color: blue;
          selection-color: white;
        }

        QLineEdit:focus
        {
          background-color: white;
          border: 1px solid rgb(80,80,80);
        }

        QLineEdit:hover
        {
          background-color: white;
          border: 1px solid rgb(80,80,80);
        }
        '''
        self.knifePathEdit = QLineEdit()
        self.knifePathEdit.setStyleSheet(pathStyleSheet)
        self.knifePathEdit.setPlaceholderText("Input path in knife.zip.(e.g. src\\)")
        self.knifePathEdit.editingFinished.connect(self.saveKnifePath)

        # set layout
        cellLayout = QGridLayout()
        cellLayout.addWidget(fileIconBtn, 0, 0)
        cellLayout.addWidget(fileNameLabel, 0, 1)
        cellLayout.addWidget(self.knifePathEdit, 1, 0, 1, 2)
        cellLayout.setContentsMargins(4, 4, 4, 4)
        cellLayout.setSpacing(0)
        self.setLayout(cellLayout)

    def saveKnifePath(self):
        if self.knifePathEdit.text().startswith(os.path.sep):
            self.knifePathEdit.setText(self.knifePathEdit.text()[1:])
        self.localToKnifeCopy[self.fileFullPath] = self.knifePathEdit.text()

    def __del__(self):
        del self.localToKnifeCopy[self.fileFullPath]


def initLog():
    if not os.path.exists("log"):
        os.makedirs("log")

def main():
    initLog()
    log_fp = open("log/run.log", 'w')
    try:
        app = QApplication(sys.argv)
        ex = KnifeUI()
        sys.exit(app.exec_())
    except Exception as e:
        log_fp.write(e.msg + '\n')
    finally:
        log_fp.close()


if __name__ == '__main__':
    main()
