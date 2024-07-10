# 6SV LUT based GEO sensor atmospheric correction
Code for Himawari-8/9 Atmospheric corretction based on 6SV LUT
# Himawari-8/AHI Land Surface Reflectance
Version 0  Year 2018-2019: ​ftp://modis.cr.chiba-u.ac.jp/ichii/SEND_NEW/H8AHI_SR/
Condition:
This is a preliminary dataset and will be updated based on the process of revision of below two papers. At this stage, please contact to Kazuhito Ichii (ichii@chiba-u.jp) for more information (e.g. format etc.).

## **_Comment in detail writen in main.py and SR_FD_1km.ipynb_**
## Data required
### **_1.CAMSRA EAC4 (Atmospheric and Aerosol data)_**
    Detail see https://ads.atmosphere.copernicus.eu/cdsapp#!/dataset/cams-global-reanalysis-eac4?tab=overview
    
### **_2.Angular data_**
    Including Solar zenith,Solar azimuth,View zenith and View azimuth angle. 
### **_3.DEM data_**
### **_4.Spectral Response Function_**
### **_5.Landmask_**
    Create from MODIS landcover data , fill ocean and water with False, land with True.

## Pre-processing
    1. Download atmospheric and aerosol data (see), and save into different folder.
    
    2. Creat Spectral Response Function for 6SV format

    3. Creat LUT for other sensor (if need)

## Revise main.py
### **_1.Input data folder path_**
    SZA_PATH = ''
    SAA_PATH = ''
    LUT_PATH = ''
    CAMS_PATH = ''
    DN_PATH = ''
    CAMS_AERO_PATH = ''
    func read_AHI_AL(res),def read_AHI_VA(res)
    
### **_2.class H8_data_**
    Need to re-writhe an function for read TOA reflectance data
## Revise SR_FD_?km.ipynb    
### **_1.func def SR_Process(band)_**
    Need to revised with other sensor, from ####Read AHI data
### **_2.Set parameters_** 
    Different band need to set with correspond parameters.
    
# References:
_Li W, K. Ichii, B. Zhang, Y. Yamamoto, W. Yang, T. Miura, H. Yoshioka, M. Matsuoka, K. Obata, R.C. Sharma, H. Yamamoto, H. Irie, P. Khatri, B. Liley, I. Morino, H. Takenaka, A. Higuchi (in revision) Estimating land surface reflectance from a next-generation geostationary meteorological satellite, Himawari 8/9 AHI. Journal of Meteorological Society of Japan._

_Zhang B., K. Ichii, W. Li, Y. Yamamoto, W. Yang, R.C. Sharma, H. Yoshioka, K. Obata, M. Matsuoka, T. Miura (in revision) Evaluation of Himawari-8 AHI land surface reflectance at mid-latitudes using LEO sensors with off-nadir observation. Remote Sensing of Environment._
