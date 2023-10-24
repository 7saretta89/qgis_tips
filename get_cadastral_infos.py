# -*- coding: utf-8 -*-

"""
-------------PASTE THE CODE INTO A NEW PYTHON SCRIPT IN QGIS----------------

ITALIAN CADASTRAL INFORMATIONS FOR A POINT LAYER
THE LAYER NEEDS TO HAVE PRECONFIGURED FIELDS:
"regione", "provincia", "comune", "sezione", "foglio", "particella"
AND "nome_point" (CHANGE IT WITH FID, ID OR WHATELSE)

IT IS NEEDED THE LIST OF "Agenzia delle Entrate" COMUNAL CODES YOU CAN FIND IT ON MY GITHUB TOO.
CHANGE THE PATH PROPERLY!
"""

from qgis.PyQt.QtCore import QCoreApplication, QFileInfo
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFeatureSink,
                       QgsProject,
                       QgsVectorLayer,
                       QgsDataSourceUri,
                       QgsFeatureRequest,
                       QgsGeometry,
                       QgsPointXY
                       )
from qgis.utils import *  
from qgis.gui import *
from qgis import processing
import requests
import csv
import os
import sys
import re



class POINTS_getComProvReg4(QgsProcessingAlgorithm):
   
    INPUT2 = 'INPUT2'

    def tr(self, string):
        
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return POINTS_getComProvReg4()

    def name(self):
        
        return 'POINTS_getComProvReg4'

    def displayName(self):
        
        return self.tr('POINTS GetComProvReg4')

    def group(self):
        
        return self.tr('my_script Scripts')

    def groupId(self):
        
        return 'my_script'

    def shortHelpString(self):
        
        return self.tr("Adding informations in the existing fields Regione, Provincia and Comune to the points entered in the input layer")

    
    def initAlgorithm(self, config=None):
        
        # We add the input vector features source. It can have point
        # geometry.
        
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT2,
                self.tr('Input layer PUNTI'),
                [QgsProcessing.TypeVectorPoint]
            )
        )

        
    

    def processAlgorithm(self, parameters, context, feedback):
        
        source = self.parameterAsVectorLayer(
            parameters,
            self.INPUT2,
            context
        )
        #exception if source not found
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT2))

        ################### MAIN OF MY SCRIPT
        
        punti = source
        feedback.pushInfo(f"the layer has {str(len( list( punti.getFeatures() ) ))} elements")
        
        
        punti.startEditing()
        
        
        #here I need to know if a point has changed position or if a point has been inserted
        #I can handle both the cases comparing the x and y values with the x and y columns
        
        for feature in punti.getFeatures():
            
            # Get the actual x and y coordinates from the geometry
            point_geom = feature.geometry()
            x, y = point_geom.asPoint()
            
            # Get the attribute values from the "name", "x" and "y" columns
            x_attr = feature["x"]
            y_attr = feature["y"]
            nome_point = feature["nome_point"]
            
            # Check if the attribute values match the actual coordinates
            if x_attr != x or y_attr != y:
                # If they don't match, update the attribute values and start the cadastral infos updating
                feedback.pushInfo(f"{nome_point} point needs to be updated! Starting the query...")
                
                feature["x"] = x
                feature["y"] = y
                
                infos = self.calcola(self, feature, feedback)
                
                punti.updateFeature(feature)
                feedback.pushInfo(f"{nome_point}:{infos}")
            
            else:
                feedback.pushInfo(f"{nome_point}: No changes")

        # Save changes and stop the edit session
        punti.commitChanges()

        # Refresh the layer
        punti.triggerRepaint()
       
        # Return the results of the algorithm. In this case just a message
        return  {"WELL DONE": punti.id()}


    """
    this function is the one you can find here:
    <script src="https://gist.github.com/pigreco/86589dddf5a59b3a7650267d5af237bd.js"></script>
    """
    
    @staticmethod
    def ade(xx, yy, EPSG, feature, parent):
    
        req = "https://wms.cartografia.agenziaentrate.gov.it/inspire/wms/ows01.php?REQUEST=GetFeatureInfo&SERVICE=WMS&SRS="+EPSG+"&STYLES=&VERSION=1.1&FORMAT=image/png&BBOX="+str(xx-1)+","+str(yy-1)+","+str(xx+1)+","+str(yy+1)+"&HEIGHT=9&WIDTH=9&LAYERS=CP.CadastralParcel&QUERY_LAYERS=CP.CadastralParcel&INFO_FORMAT=text/html&X=5&Y=5"

        r = requests.get(req, auth=('user', 'pass'))
        a = r.text.partition("InspireId localId</th><td>")[2]
        b = a.partition("</td>")[0]
        return b
    
    """
    this one gets he right path for the list of Cadastral Codes
    --------------------------------------------
    HERE CHANGE THE PATH!!!!
    -------
    """
    @staticmethod
    def getpath(feedback):
    
        feedback.pushInfo('Get infos from Cadastral codes list...')
        # Get the current user's home directory
        home_directory = os.path.expanduser("~")
        # Split the home directory path
        path_parts = home_directory.split(os.path.sep)
        # Find the position of the 'Users' folder in the path
        users_index = path_parts.index('Users')
        # The user's name is the next part of the path
        user_name = path_parts[users_index + 1]
        # Construct the full path to the AppData/Roaming folder
        path = os.path.join(home_directory, 'Desktop/lista_comuni_ADE')
        return(path)
    
    """
    this one reads and extracts the needed infos from the code list
    """
    @staticmethod
    def cod_com(cod_comune, indice, path):
    
        list_row = []
        with open(path + '/lista_cod_comune.csv') as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            
            for row in csv_reader:
                if cod_comune in row:
                    return row [indice]
    
    """
    this one is the function that writes into the layer the cadastral infos
    """
    @staticmethod    
    def calcola(self, point, feedback):
        
        #PATTERN CODICE CATASTO
        pattern = '^(.+)\\.(.+)\\.(.+)\\.(.{4})(.)(.+)\\.(.+)'
        
        path = self.getpath(feedback)
        feedback.pushInfo('Get Cadastral String for the feature...')

                    
        geo = QgsGeometry.asPoint(point.geometry())#get the geometry of the feature
        pxy = QgsPointXY(geo)
            
        codice_catasto = self.ade(pxy.x(), pxy.y(), 'EPSG:3045', 'a', 'b')
        
        #check if cadastral code is available
        if not codice_catasto:
            return ('NO CADASTRAL CODE AVAILABLE!')
        else:
            feedback.pushInfo(f"Cadastral code: {codice_catasto}")
            #cat è il codice comunale
            cat = codice_catasto[11:15]
            feedback.pushInfo(f"Comunal code:{cat}")    
                
            code = codice_catasto
            match = re.match(pattern, code)
            if match:
                section = match.group(5)
                sheet = match.group(6)[:-2]
                parcel = match.group(7)
                feedback.pushInfo(f"Sheet: {sheet}, Parcel: {parcel}, Section: {section}. Comunal code: {cat}")
            else:
                print(f"Invalid format: {code}")
                

            comune = self.cod_com(cat, 1, path)
            provincia = self.cod_com(cat, 2, path)
            regione = self.cod_com(cat, 3, path)
            
            point["regione"] = regione
            point["provincia"] = provincia
            point["comune"] = comune
            point["sezione"] = section
            point["foglio"] = sheet
            point["particella"] = parcel
            
            return ('changes done!')
