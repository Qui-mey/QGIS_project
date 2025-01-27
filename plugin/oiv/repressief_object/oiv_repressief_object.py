"""initialize al action for repressief object"""
import os

from qgis.PyQt import uic
import qgis.PyQt.QtWidgets as PQtW
import qgis.core as QC

import oiv.helpers.utils_core as UC
import oiv.helpers.utils_gui as UG
import oiv.tools.editFeature as EF
import oiv.tools.stackwidget as SW
import oiv.tools.import_file as IFW
import oiv.repressief_object.oiv_object_tekenen as OTW
import oiv.repressief_object.oiv_create_grid as GW
import oiv.werkvoorraad.oiv_werkvoorraad as OWW
import oiv.helpers.messages as MSG
import oiv.helpers.drawing_helper as DH
import oiv.helpers.constants as PC
import oiv.helpers.qt_helper as QT
import oiv.tools.print as PR

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), PC.OBJECT["objectwidgetui"]))


class oivRepressiefObjectWidget(PQtW.QDockWidget, FORM_CLASS):
    """interactive UI management"""

    attributeform = None
    identifier = None
    snapLayerNames = DH.ROSNAPLAYERS
    tekensymbolenwidget = None
    importwidget = None
    gridWidget = None

    def __init__(self, parent=None, objectId=None, formeleNaam=None):
        super(oivRepressiefObjectWidget, self).__init__(parent)
        self.setupUi(self)
        self.parent = parent
        self.iface = parent.iface
        self.canvas = parent.canvas
        self.object_id.setVisible(False)
        self.selectTool = parent.selectTool
        self.polygonSelectTool = parent.polygonSelectTool
        self.pointTool = parent.pointTool
        self.drawTool = parent.drawTool
        self.moveTool = parent.moveTool
        self.identifyTool = parent.identifyTool
        self.object_id.setText(str(objectId))
        self.formelenaam.setText(formeleNaam)
        UG.set_lengte_oppervlakte_visibility(self, False, False, False, False)
        self.initActions()

    def initActions(self):
        """connect the buttons to their actions"""
        self.identify.setVisible(False)
        self.delete_f.setVisible(False)
        self.pan.setVisible(False)
        self.terrein_tekenen.setVisible(False)
        self.terug.clicked.connect(self.close_repressief_object_show_base)
        self.objectgegevens.clicked.connect(self.run_objectgegevens_bewerken)
        self.terugmelden.clicked.connect(self.open_bgt_viewer)
        self.delete_object.clicked.connect(self.run_delete_object)
        self.terrein_bewerken.clicked.connect(self.object_terrein_bewerken)
        self.object_symbolen.clicked.connect(self.run_object_symbolen_tekenen)
        self.object_print.clicked.connect(self.run_print)
        self.create_grid.clicked.connect(self.run_create_grid)
        self.import_drawing.clicked.connect(self.run_import)
        self.btn_werkvoorraad.clicked.connect(self.run_werkvoorraad)
        self.helpBtn, self.floatBtn, titleBar = QT.getTitleBar()
        self.setTitleBarWidget(titleBar)
        self.helpBtn.clicked.connect(lambda: UC.open_url(PC.HELPURL["repressiefobjecthelp"]))
        self.floatBtn.clicked.connect(lambda: self.setFloating(True))
        self.check_werkvoorraad()

    def check_werkvoorraad(self):
        objectId = self.object_id.text()
        layerName = 'Werkvoorraad objecten'
        ilayer = UC.getlayer_byname(layerName)
        request = QC.QgsFeatureRequest().setFilterExpression('"id" = ' + str(objectId))
        it = ilayer.getFeatures(request)
        if len(list(it)) > 0:
            self.btn_werkvoorraad.setEnabled(True)
        else:
            self.btn_werkvoorraad.setEnabled(False)

    def close_repressief_object_show_base(self):
        """close this gui and return to the main page"""
        self.delete_object.clicked.disconnect()
        self.terug.clicked.disconnect()
        self.objectgegevens.clicked.disconnect()
        self.terugmelden.clicked.disconnect()
        self.terrein_bewerken.clicked.disconnect()
        self.object_print.clicked.disconnect()
        self.helpBtn.clicked.disconnect()
        self.floatBtn.clicked.disconnect()
        try:
            self.terrein_tekenen.clicked.disconnect()
            self.delete_f.clicked.disconnect()
            self.pan.clicked.disconnect()
        except:  # pylint: disable=bare-except
            pass
        self.close()
        self.parent.show()
        del self

    def activatePan(self):
        """activate pan to lose other draw features"""
        self.iface.actionPan().trigger()

    def run_objectgegevens_bewerken(self):
        """select bouwlaag on canvas to edit the atrribute form"""
        objectId = self.object_id.text()
        request = QC.QgsFeatureRequest().setFilterExpression('"id" = ' + str(objectId))
        ilayer = UC.getlayer_byname(PC.OBJECT["objectlayername"])
        try:
            ifeature = UC.featureRequest(ilayer, request)
            if ifeature:
                self.edit_attribute(ilayer, ifeature)
        except StopIteration:
            MSG.showMsgBox('no_objectid')

    def open_bgt_viewer(self):
        """open url based on BGT location, i.v.m. terugmelden"""
        e = self.canvas.extent()
        gemx = (e.xMaximum() + e.xMinimum())/2
        gemy = (e.yMaximum() + e.yMinimum())/2
        url = PC.OBJECT["bgtviewerurl"] + 'geometry.x=' + str(gemx) + '&geometry.y=' + str(gemy) + '&zoomlevel=12'
        UC.open_url(url)

    def run_delete_object(self):
        """delete repressief object"""
        ifeature = None
        ilayer = UC.getlayer_byname(PC.OBJECT["objectlayername"])
        objectId = self.object_id.text()
        request = QC.QgsFeatureRequest().setFilterExpression('"id" = ' + str(objectId))
        ifeature = UC.featureRequest(ilayer, request)
        ilayer.startEditing()
        ilayer.selectByIds([ifeature.id()])
        reply = MSG.showMsgBox('deleteobject')
        if not reply:
            #als "nee" deselecteer alle geselecteerde features
            ilayer.selectByIds([])
        elif reply:
            #als "ja" -> verwijder de feature op basis van het unieke feature id
            ilayer.deleteFeature(ifeature.id())
            ilayer.commitChanges()
            reply = MSG.showMsgBox('deletedobject')
        UC.refresh_layers(self.iface)
        self.close_repressief_object_show_base()

    def edit_attribute(self, ilayer, ifeature):
        """open het formulier van een feature in een dockwidget, zodat de attributen kunnen worden bewerkt"""
        stackWidget = SW.oivStackWidget()
        self.iface.addDockWidget(QT.getWidgetType(), stackWidget)
        stackWidget.parentWidget = self
        stackWidget.parentWidth = self.width()
        stackWidget.open_feature_form(ilayer, ifeature)
        self.close()
        layerNames = PC.OBJECT["nogeotables"]
        for name in layerNames:
            layer = UC.getlayer_byname(name)
            layer.updateExtents()
        stackWidget.show()
        try:
            self.selectTool.geomSelected.disconnect(self.edit_attribute)
        except: # pylint: disable=bare-except
            pass

    def object_terrein_bewerken(self):
        """draw repressief object terrain"""
        self.identify.setVisible(True)
        self.delete_f.setVisible(True)
        self.pan.setVisible(True)
        self.terrein_tekenen.setVisible(True)
        self.terrein_tekenen.clicked.connect(self.run_terrein_toevoegen)
        self.delete_f.clicked.connect(self.run_delete_terrein)
        self.pan.clicked.connect(self.activatePan)
        self.identify.clicked.connect(self.edit_feature)

    def edit_feature(self):
        self.selectTool.whichConfig = PC.OBJECT["configtable"]
        self.canvas.setMapTool(self.selectTool)
        self.selectTool.geomSelected.connect(self.edit_attribute)

    def run_create_grid(self):
        gridWidget = GW.oivGridWidget(self)
        gridWidget.object_id.setText(self.object_id.text())
        self.iface.addDockWidget(QT.getWidgetType(), gridWidget)
        gridWidget.show()
        self.close()

    def run_terrein_toevoegen(self):
        objectId = self.object_id.text()
        possibleSnapFeatures = UC.get_possible_snapFeatures_object(self.snapLayerNames, objectId)
        self.drawTool.parent = self
        self.drawTool.layer = UC.getlayer_byname(PC.OBJECT["terreinlayername"])
        UG.set_lengte_oppervlakte_visibility(self, True, True, True, True)
        self.drawTool.possibleSnapFeatures = possibleSnapFeatures
        self.drawTool.canvas = self.canvas
        self.drawTool.onGeometryAdded = self.place_object_terrein
        self.drawTool.captureMode = 2
        self.canvas.setMapTool(self.drawTool)

    def run_delete_terrein(self):
        self.selectTool.whichConfig = PC.OBJECT["configtable"]
        self.canvas.setMapTool(self.selectTool)
        self.selectTool.geomSelected.connect(self.delete)

    def delete(self, ilayer, ifeature):
        deleteLayerNames = [PC.OBJECT["objectlayername"], PC.OBJECT["terreinlayername"]]
        reply = EF.delete_feature(ilayer, ifeature, deleteLayerNames, self.iface)
        if reply == 'Retry':
            self.run_delete_terrein()
        self.selectTool.geomSelected.disconnect(self.delete)

    def place_object_terrein(self, points, _dummy):
        """save drawn terrain"""
        layer = UC.getlayer_byname(PC.OBJECT["terreinlayername"])
        if points:
            parentId, childFeature = UC.construct_feature('Polygon', PC.OBJECT["objectlayername"], points, self.object_id.text())
        if parentId is not None:
            buttonCheck = UC.get_attributes(parentId, childFeature, None, None, layer, PC.OBJECT["configtable"])
            if buttonCheck != 'Cancel':
                UC.write_layer(layer, childFeature)
        layer.commitChanges()
        layer.triggerRepaint()
        self.activatePan()

    def run_object_symbolen_tekenen(self):
        tekenWidget = OTW.oivObjectTekenWidget(self)
        self.iface.addDockWidget(QT.getWidgetType(), tekenWidget)
        tekenWidget.show()
        self.close()

    def run_werkvoorraad(self):
        werkvoorraadWidget = OWW.oivWerkvoorraadWidget(self)
        werkvoorraadWidget.bouwlaagOfObject = 'Object'
        self.iface.addDockWidget(QT.getWidgetType(), werkvoorraadWidget)
        werkvoorraadWidget.initUI()
        werkvoorraadWidget.show()
        self.close()

    def run_print(self):
        directory = PQtW.QFileDialog().getExistingDirectory()
        fileName = self.object_id.text() + '_' + self.formelenaam.text()
        filterString = '"object_id"={}'.format(self.object_id.text())
        PR.load_composer(directory, 'object', filterString, fileName)
        MSG.showMsgBox('print_finished', directory)

    def run_import(self):
        """initiate import widget"""
        importwidget = IFW.oivImportFileWidget(self)
        self.iface.addDockWidget(QT.getWidgetType(), importwidget)
        self.close()
        importwidget.show()
