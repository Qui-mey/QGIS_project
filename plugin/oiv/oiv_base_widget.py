"""init the oiv base widget"""
import os

from qgis.PyQt import uic
import qgis.PyQt.QtCore as PQtC
import qgis.PyQt.QtWidgets as PQtW
import qgis.core as QC

import oiv.tools.filter_object as FO
import oiv.helpers.qt_helper as QT
import oiv.helpers.messages as MSG
from .helpers.constants import PLUGIN, PAND, OBJECT, HELPURL, bagpand_layername
import oiv.helpers.utils_core as UC
import oiv.bag_pand.oiv_pandgegevens as OPG
import oiv.repressief_object.oiv_repressief_object as ORO
import oiv.repressief_object.oiv_objectnieuw as OON
import oiv.info_of_interest.oiv_info_of_interest as IOI

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), PLUGIN["basewidget"]))


class oivBaseWidget(PQtW.QDockWidget, FORM_CLASS):
    """create dockwidget as base of the oiv plugin"""

    def __init__(self, parent=None):
        """Constructor."""
        super(oivBaseWidget, self).__init__(parent)
        self.setupUi(self)
        self.parent = parent
        self.iface = parent.iface
        self.canvas = parent.canvas
        self.pinTool = parent.pinTool
        self.pointTool = parent.pointTool
        self.selectTool = parent.selectTool
        self.polygonSelectTool = parent.polygonSelectTool
        self.identifyTool = parent.identifyTool
        self.drawTool = parent.drawTool
        self.moveTool = parent.moveTool
        self.initUI()

    def initUI(self):
        self.identify_pand.clicked.connect(self.run_identify_pand)
        self.identify_gebouw.clicked.connect(self.run_identify_terrein)
        self.filter_objecten.clicked.connect(lambda: FO.init_filter_section(self))
        self.filterBtn.clicked.connect(lambda: FO.set_object_filter(self))
        self.info_of_interest.clicked.connect(self.run_info_of_interest)
        self.closewidget.clicked.connect(self.close_basewidget)
        self.filterframe.setVisible(False)
        self.helpBtn, self.floatBtn, titleBar = QT.getTitleBar()
        self.setTitleBarWidget(titleBar)
        self.helpBtn.clicked.connect(lambda: UC.open_url(HELPURL["basewidgethelp"]))
        self.floatBtn.clicked.connect(lambda: self.setFloating(True))

    def run_identify_pand(self):
        """get the identification of a building from the user"""
        self.canvas.setMapTool(self.identifyTool)
        try:
            self.identifyTool.geomIdentified.disconnect()
        except: # pylint: disable=bare-except
            pass
        self.identifyTool.geomIdentified.connect(self.get_identified_pand)

    def run_identify_terrein(self):
        """get the identification of a building from the user"""
        self.canvas.setMapTool(self.identifyTool)
        try:
            self.identifyTool.geomIdentified.disconnect()
        except: # pylint: disable=bare-except
            pass
        self.identifyTool.geomIdentified.connect(self.get_identified_terrein)

    def get_identified_pand(self, ilayer, ifeature):
        """Return of identified layer and feature and get related object"""
        #the identified layer must be "Bouwlagen" or "BAG panden"
        if isinstance(ilayer, QC.QgsVectorLayer):
            if ilayer.name() == PAND["bouwlaaglayername"]:
                objectId = str(ifeature["pand_id"])
                self.run_bouwlagen(objectId)
            elif ilayer.name() == bagpand_layername():
                objectId = str(ifeature["identificatie"])
                self.run_bouwlagen(objectId)
        #if another layer is identified there is no object that can be determined, so a message is send to the user
        else:
            MSG.showMsgBox('noidentifiedobject')
        self.identifyTool.geomIdentified.disconnect()

    def get_identified_terrein(self, ilayer, ifeature):
        """Return of identified layer and feature and get related object"""
        #the identified layer must be "Object" or "Object terrein"
        drawLayer = UC.getlayer_byname(OBJECT["objectlayername"])
        if ilayer is None:
            self.run_new_object('wordt gekoppeld in de database', 'BGT', 'wordt gekoppeld in de database')
        elif ilayer.name() == bagpand_layername() and "PDOK" in ilayer.name():
            objectId = str(ifeature["identificatie"])
            bron = "BAG"
            bron_tabel = "Pand"
            self.run_new_object(objectId, bron, bron_tabel)
        elif ilayer.name() == bagpand_layername():
            objectId = str(ifeature["identificatie"])
            bron = ifeature["bron"]
            bron_tabel = ifeature["bron_tbl"]
            self.run_new_object(objectId, bron, bron_tabel)
        elif ilayer.name() == OBJECT["objectlayername"]:
            objectId = ifeature["id"]
            formeleNaam = ifeature["formelenaam"]
            self.run_object(formeleNaam, objectId)
        elif ilayer.name() == OBJECT["terreinlayername"]:
            objectId = ifeature["object_id"]
            request = QC.QgsFeatureRequest().setFilterExpression('"id" = ' + str(objectId))
            ifeature = UC.featureRequest(drawLayer, request)
            if ifeature:
                formeleNaam = ifeature["formelenaam"]
                self.run_object(formeleNaam, objectId)
        #if another layer is identified there is no object that can be determined, so a message is send to the user
        else:
            MSG.showMsgBox('noidentifiedobject')
        self.identifyTool.geomIdentified.disconnect()

    def run_bouwlagen(self, objectId):
        """start objectgegevens widget"""
        pandwidget = OPG.oivPandWidget(self, objectId)
        self.iface.addDockWidget(QT.getWidgetType(), pandwidget)
        self.iface.actionPan().trigger()
        pandwidget.show()
        self.close()

    def run_object(self, formeleNaam, objectId):
        """start repressief object widget"""
        repressiefObjectWidget = ORO.oivRepressiefObjectWidget(self, objectId, formeleNaam)
        self.iface.addDockWidget(QT.getWidgetType(), repressiefObjectWidget)
        self.iface.actionPan().trigger()
        repressiefObjectWidget.show()
        self.close()

    def run_new_object(self, objectId, bron, bron_tbl):
        """start new object widget, eventhough passing trough the tools to objectgegevens widget"""
        objectNieuwWidget = OON.oivObjectNieuwWidget(self, objectId, bron, bron_tbl)
        self.iface.addDockWidget(QT.getWidgetType(), objectNieuwWidget)
        self.iface.actionPan().trigger()
        objectNieuwWidget.show()
        self.close()
        
    def run_info_of_interest(self):
        """start objectgegevens widget"""
        interestWidget = IOI.oivInfoOfInterestTekenWidget(self)
        self.iface.addDockWidget(QT.getWidgetType(), interestWidget)
        self.iface.actionPan().trigger()
        interestWidget.show()
        self.close()

    def close_basewidget(self):
        """close plugin and re-activate toolbar combobox"""
        self.close()
        self.parent.toolbar.setEnabled(True)
        self.parent.projCombo.setEnabled(True)
        self.parent.checkVisibility = False
