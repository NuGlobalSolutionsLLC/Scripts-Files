Place here all the shapefiles you want converted into GeoJSONs.

They need to be in WGS 1984 coord system.

These files should have the following fields (they are case sensitive):

- Well_ID
- SDate
- Matrix
- Analyte
- Result
- Lab_Flag
- Units
- X_Coord
- Y_Coord

For Plume Contours, you should have the following fields:
- FID
- Name
- FolderPath
- SymbolID
- AltMode
- Base
- Clamped
- Extruded
- Snippet
- PopupInfo
- Shape_Leng
- Shape_Area
------------------------------------------------------------------
For transect Series2, you should have the following fields:
- Id
- Name
- StartX
- StartY
- EndX
- EndY
- Length
- hyperlink = s2aa_mr.html