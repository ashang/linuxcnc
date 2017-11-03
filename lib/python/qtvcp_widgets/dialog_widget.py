#!/usr/bin/env python
# QTVcp Widget - MDI edit line widget
# This widgets displays linuxcnc axis position information.
#
# Copyright (c) 2017 Chris Morley
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

import os
from PyQt4.QtGui import QMessageBox, QFileDialog, QColor
from PyQt4.QtCore import Qt, pyqtSlot, pyqtProperty
from qtvcp_widgets.simple_widgets import _HalWidgetBase, hal
from qtvcp.qt_glib import GStat, Lcnc_Action

# Instiniate the libraries with global reference
# GSTAT gives us status messages from linuxcnc
# ACTION gives commands to linuxcnc
GSTAT = GStat()
ACTION = Lcnc_Action()

class Lcnc_Dialog(QMessageBox):
    def __init__(self, parent = None):
        QMessageBox.__init__(self,parent)
        self.setTextFormat(Qt.RichText)
        self.setText('<b>Do you want to shutdown now?</b>')
        self.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        self.setIcon(QMessageBox.Critical)
        self.setDetailedText('You can set a preference to not see this message')
        self.OK_TYPE = 1
        self.YN_TYPE = 0
        self._state = False
        self.hide()

    def showdialog(self, message, more_info=None, details=None, display_type=1,
                     icon=QMessageBox.Information, pinname=None):
        self.OK_TYPE = 1
        self.YN_TYPE = 0
        self.QUESTION = QMessageBox.Question
        self.INFO = QMessageBox.Information
        self.WARNING = QMessageBox.Warning
        self.CRITICAL = QMessageBox.Critical
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlags( self.windowFlags() |Qt.Tool |
                 Qt.FramelessWindowHint | Qt.Dialog |
                 Qt.WindowStaysOnTopHint |Qt.WindowSystemMenuHint)
        self.setIcon(icon)
        self.setText('<b>%s</b>'% message)
        if more_info:
            self.setInformativeText(more_info)
        else:
           self.setInformativeText('')
        if details:
            self.setDetailedText(details)
        if display_type == self.OK_TYPE:
            self.setStandardButtons(QMessageBox.Ok)
        else:
            self.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        self.buttonClicked.connect(self.msgbtn)

        retval = self.exec_()
        print "value of pressed message box button:", retval
        if retval == QMessageBox.No:
            return False
        else:
            return True

    def msgbtn(self, i):
        return
        print "Button pressed is:",i.text()

    #**********************
    # Designer properties
    #**********************
    @pyqtSlot(bool)
    def setState(self, value):
        self._state = value
        if value:
            self.show()
        else:
            self.hide()
    def getState(self):
        return self._state
    def resetState(self):
        self._state = False
    state = pyqtProperty(bool, getState, setState, resetState)

################################################################################
# Tool Change Dialog
################################################################################
class Lcnc_ToolDialog(Lcnc_Dialog, _HalWidgetBase):
    def __init__(self, parent=None):
        super(Lcnc_ToolDialog, self).__init__(parent)
        self.setText('<b>Manual Tool Change Request</b>')
        self.setInformativeText('Please Insert Tool 0')
        self.setStandardButtons(QMessageBox.Ok)
        self._color = QColor(0, 0, 0, 150)

    # We want the tool change HAL pins the same as whats used in AXIS so it is
    # easier for users to connect to.
    # So we need to trick the HAL component into doing this for these pins,
    # but not anyother Qt widgets.
    # So we record the original base name of the component, make our pins, then
    # switch it back
    def _hal_init(self):
        _HalWidgetBase._hal_init(self)
        oldname = self.hal.comp.getprefix()
        self.hal.comp.setprefix('hal_manualtoolchange')
        self.hal_pin = self.hal.newpin('change', hal.HAL_BIT, hal.HAL_IN)
        self.hal_pin.value_changed.connect(self.tool_change)
        self.tool_number = self.hal.newpin('number', hal.HAL_S32, hal.HAL_IN)
        self.changed = self.hal.newpin('changed', hal.HAL_BIT, hal.HAL_OUT)
        #self.hal_pin = self.hal.newpin(self.hal_name + 'change_button', hal.HAL_BIT, hal.HAL_IN)
        self.hal.comp.setprefix(oldname)

    def showtooldialog(self, message, more_info=None, details=None, display_type=1,
                     icon=QMessageBox.Information):

        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlags( self.windowFlags() |Qt.Tool |
                 Qt.FramelessWindowHint | Qt.Dialog |
                    Qt.WindowStaysOnTopHint |Qt.WindowSystemMenuHint)
        self.setIcon(icon)
        self.setTextFormat(Qt.RichText)
        self.setText('<b>%s</b>'% message)
        if more_info:
            self.setInformativeText(more_info)
        else:
           self.setInformativeText('')
        if details:
            self.setDetailedText(details)
        if display_type == self.OK_TYPE:
            self.setStandardButtons(QMessageBox.Ok)
        else:
            self.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            self.setDefaultButton(QMessageBox.Ok)
        retval = self.exec_()
        if retval == QMessageBox.Cancel:
            return False
        else:
            return True

    def tool_change(self, change):
        if change:
                answer = self.do_message(change)
                if answer:
                    self.changed.set(True)
                else:
                    # TODO add abort command
                    print 'cancelled should abort'
        elif not change:
            self.changed.set(False)

    def do_message(self,change):
        if change and not self.changed.get():
            MORE = 'Please Insert Tool %d'% self.tool_number.get()
            MESS = 'Manual Tool Change Request'
            DETAILS = ' Tool Info:'
            GSTAT.emit('focus-overlay-changed',True,MESS, self._color)
            result = self.showtooldialog(MESS,MORE,DETAILS)
            GSTAT.emit('focus-overlay-changed',False,None,None)
            return result

    #**********************
    # Designer properties
    #**********************

    def getColor(self):
        return self._color
    def setColor(self, value):
        self._color = value
    def resetState(self):
        self._color = QColor(0, 0, 0,150)

    color = pyqtProperty(QColor, getColor, setColor)

################################################################################
# File Open Dialog
################################################################################
class Lcnc_FileDialog(QFileDialog, _HalWidgetBase):
    def __init__(self, parent=None):
        super(Lcnc_FileDialog, self).__init__(parent)
        self._state = False
        self._color = QColor(0, 0, 0, 150)

    def _hal_init(self):
            GSTAT.connect('load-file-request', lambda w: self.load_dialog())

    def load_dialog(self):
        GSTAT.emit('focus-overlay-changed',True,'Open Gcode',self._color)
        fname = QFileDialog.getOpenFileName(None, 'Open file',
                os.path.join(os.path.expanduser('~'), 'linuxcnc/nc_files/examples'))
        GSTAT.emit('focus-overlay-changed',False,None,None)
        if fname:
            #NOTE.notify('Error',str(fname),QtGui.QMessageBox.Information,10)
            f = open(fname, 'r')
            ACTION.OPEN_PROGRAM(fname)
            GSTAT.emit('file-loaded', fname)
        return fname

    #**********************
    # Designer properties
    #**********************

    @pyqtSlot(bool)
    def setState(self, value):
        self._state = value
        if value:
            self.show()
        else:
            self.hide()
    def getState(self):
        return self._state
    def resetState(self):
        self._state = False
    state = pyqtProperty(bool, getState, setState, resetState)

    def getColor(self):
        return self._color
    def setColor(self, value):
        self._color = value
    def resetState(self):
        self._color = QColor(0, 0, 0,150)


    color = pyqtProperty(QColor, getColor, setColor)
################################
# for testing without editor:
################################
def main():
    import sys
    from PyQt4.QtGui import QApplication

    app = QApplication(sys.argv)
    widget = Lcnc_ToolDialog()
    widget.show()
    sys.exit(app.exec_())
if __name__ == "__main__":
    main()


