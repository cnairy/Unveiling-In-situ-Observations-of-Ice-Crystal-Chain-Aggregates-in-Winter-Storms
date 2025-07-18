cpi_imagedump.pro is the main IDL script to make the CPI collages. 

Requirments: IDL Licence, and Coyote Package

Usage:
IDL> !PATH = Expand_Path('+~/CoPAS/Coyote/') + ':' + !PATH

IDL> cpi_imagedump, file_search('../../Hawkeye-CPI_Data/*.roi'), res=2.3, rate=5, xpanelsize=2400, ypanelsize=2000, project='IMPACTS'
