import shutil
import numpy as np
import time as T
from joblib import Parallel, delayed
from scipy.interpolate import griddata,interpn,RegularGridInterpolator
import math
import os
import cv2
from ftplib import FTP
import threading
import xarray as xr
import paramiko
from scp import SCPClient
import subprocess
import datetime as dt
import numba as nb
import concurrent.futures
# import dask.array as da

SZA_PATH = '/data01/GEO/INPUT/ANGLE/sun/Solar_Zenith_Angle_u2/'
SAA_PATH = '/data01/GEO/INPUT/ANGLE/sun/Solar_Azimuth_Angle_u2/'

LUT_PATH = '/data01/GEO/INPUT/LUT/'
CAMS_PATH = '/data01/GEO/INPUT/ATMOSPHERE/'
DN_PATH = '/data01/GEO/INPUT/'
CAMS_AERO_PATH = '/data01/GEO/INPUT/AEROSOL_TYPE/'


sza = np.linspace(0,80,17)
vza = np.linspace(0,80,17)
water = np.linspace(0,7,8)
ozone = np.linspace(0.2,0.4,5)
AOT = np.array([0.01,0.05,0.1,0.15,0.2,0.3,0.4,0.6,0.8,1.0,1.5,2.0])
raa = np.linspace(0,180,19)
al = np.linspace(0,8,5)
aero_type = np.array([0,1])

def read_AHI_AL(res):
    paths = {
        0.005: ('/data01/GEO/INPUT/ELEVATION_GEO/AHI/MERIT_DEM_AHI_05km.dat', 24000),
        0.01: ('/data01/GEO/INPUT/ELEVATION_GEO/AHI/MERIT_DEM_AHI_10km.dat', 12000),
        0.02: ('/data01/GEO/INPUT/ELEVATION_GEO/AHI/MERIT_DEM_AHI_20km.dat', 6000)
    }
    AL_PATH, col = paths.get(res, (None, None))
    if AL_PATH:
        with open(AL_PATH,'rb') as fp:
            AL = np.frombuffer(fp.read(),dtype='u2').reshape(col,col) * 0.001
        return AL
    else:
        return None

def read_AHI_VA(res):
    paths = {
        0.005: ('/data01/GEO/INPUT/ANGLE/Viewer_Zenith_Angle/AHI_VZA_05.dat', '/data01/GEO/INPUT/ANGLE/Viewer_Azimuth_Angle/AHI_VAA_05.dat', 24000),
        0.01: ('/data01/GEO/INPUT/ANGLE/Viewer_Zenith_Angle/AHI_VZA_10.dat', '/data01/GEO/INPUT/ANGLE/Viewer_Azimuth_Angle/AHI_VAA_10.dat', 12000),
        0.02: ('/data01/GEO/INPUT/ANGLE/Viewer_Zenith_Angle/AHI_VZA_20.dat', '/data01/GEO/INPUT/ANGLE/Viewer_Azimuth_Angle/AHI_VAA_20.dat', 6000)
    }
    VZA_PATH, VAA_PATH, col = paths.get(res, (None, None, None))
    if VZA_PATH and VAA_PATH:
        with open(VZA_PATH,'rb') as fp:
            VZA = np.frombuffer(fp.read(),dtype='u2').reshape(col,col) / 100
        with open(VAA_PATH,'rb') as fp:
            VAA = np.frombuffer(fp.read(),dtype='u2').reshape(col,col) / 100
        return VZA,VAA
    else:
        return None
    
    
    
class H8_data:
    """
    Class for handling Himawari8/AHI data

    Attributes:
        account (str): SSH account for accessing the remote server
        pw (str): SSH password for accessing the remote server
        band (str): Band name of the AHI data ("vis", "nir", or "swir")
        band_number (str): Band number of the AHI data
        date (str): Date of the AHI data in the format "YYYYMMDDHHMM"
        sava_path (str): Path for saving the downloaded data
    """

    def __init__(self, account, pw, band, band_number, date, save_path):
        self.account = account
        self.pw = pw
        self.band = band
        self.band_number = band_number
        self.date = date
        self.save_path = save_path

    def get_path(self):
        """
        Get the file path of the AHI data on the remote server

        Returns:
            str: File path of the AHI data on the remote server
        """
        return "/nfsdata02/GEO/ORGDATA/H8AHI/hmwr829gr.cr.chiba-u.ac.jp/gridded/FD/V20151105/" + self.date[:6] + "/" + self.band.upper() + "/"

    def get_filename(self):
        """
        Get the filename of the AHI data

        Returns:
            str: Filename of the AHI data
        """
        return self.date + "." + self.band + "." + self.band_number + ".fld.geoss.bz2"

    def DN2TBB(self, data):
        """
        Convert digital numbers to brightness temperatures

        Args:
            data (ndarray): A numpy array containing the digital numbers

        Returns:
            ndarray: A numpy array containing the brightness temperatures
        """
        if int(self.date[:4]) <= 2019:
            LUT = np.loadtxt(DN_PATH + "count2tbb/" + self.band + "." + self.band_number + "." + self.date[:4])
        else:
            LUT = np.loadtxt(DN_PATH + "count2tbb/" + self.band + "." + self.band_number + ".2019")
        return LUT[data, 1]

    def file_path(self):
        """
        Get the full file path of the downloaded AHI data

        Returns:
            str: Full file path of the downloaded AHI data
        """
        return self.get_path() + self.get_filename()
    def target_path(self):
        """
        Get the full file path of the downloaded AHI data

        Returns:
            str: Full file path of the downloaded AHI data
        """
        return self.save_path + self.get_filename()
    
    

#     def download_H8data(self):
#         """
#         Download the AHI data from the remote server and save it to the local directory

#         Returns:
#             str: File path of the downloaded AHI data, or "No data" if the data doesn't exist
#         """
#         client = paramiko.SSHClient()
#         client.load_system_host_keys()
#         client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#         client.connect(hostname="10.4.104.140", port=22, username=self.account, password=self.pw)
#         scp = SCPClient(client.get_transport())
#         sftp = client.open_sftp()

#         try:
#             sftp.stat(self.file_path())
#         except FileNotFoundError:
#             client.close()
#             # print("File Not Found")
#             return "No data"
#         else:
#             scp.get(self.file_path(), self.save_path + "/")
#             p = subprocess.Popen("lbzip2 -d {}{}".format(self.save_path + "/", self.file_path()[-33:]), shell=True)
#             p.communicate()
#             client.close()
#             # print("Himawari8/AHI data processed successfully")
#             return self.save_path + self.get_filename()[:-4]

    def read_H8data(self,H8_file_path):
        """
        Read the downloaded Himawari8/AHI data and convert the digital numbers (DN) to brightness temperatures (TBB)

        Returns:
            numpy.ndarray: Array of brightness temperatures
            str: "No data" if the data is not available
        """
        # H8_file_path = self.download_H8data()
        if self.band == "vis":
            sr = 12000
        elif self.band == "ext":
            sr = 24000
        else:
            sr = 6000
        if H8_file_path != 'No data':
            data = np.memmap(H8_file_path, dtype='>u2', mode='r', shape=(sr,sr))
            data = self.DN2TBB(data)
            data = data/100
            if self.band == "ext": 
                data = data.reshape(12000,2,12000,2).mean(-1).mean(1)
            # print("data reading finish")
            return data
        else:
            return 'No data'
        

class LUT_interpolator:
    """
    This class is used to read LUT files and interpolate LUT data.
    """

    def __init__(self, band):
        """
        Constructor for LUTInterpolator class.

        Args:
            lut_path (str): The path to the LUT files.
            band (int): The band number.

        """
        self.band = band
        self.fn1, self.fn2, self.fn3 = self._interpolate()

    def _interpolate(self):
        """
        Reads the LUT files and performs interpolation on LUT data.
        """
        filename1 = f"01_band{self.band}.csv"
        filename2 = f"02_band{self.band}.csv"
        filename3 = f"03_band{self.band}.csv"

        # Read the LUT data.
        X1 = np.loadtxt(LUT_PATH + filename1, delimiter=",")
        X2 = np.loadtxt(LUT_PATH + filename2, delimiter=",")
        X3 = np.loadtxt(LUT_PATH + filename3, delimiter=",")

        # Reshape the LUT data into the appropriate shape.
        if self.band in [1, 2]:
            X1 = X1.reshape(2, 5, 12, 5, 17, 17, 19)
            X2 = X2.reshape(2, 5, 12, 5, 17, 17, 19)
            X3 = X3.reshape(2, 5, 12, 5, 17, 17, 19)
            params = (aero_type, ozone, AOT, al, sza, vza, raa)
        elif self.band in [3]:
            X1 = X1.reshape(2, 8, 5, 12, 5, 17, 17, 19)
            X2 = X2.reshape(2, 8, 5, 12, 5, 17, 17, 19)
            X3 = X3.reshape(2, 8, 5, 12, 5, 17, 17, 19)
            params = (aero_type, water, ozone, AOT, al, sza, vza, raa)
        else:
            X1 = X1.reshape(2, 8, 12, 5, 17, 17, 19)
            X2 = X2.reshape(2, 8, 12, 5, 17, 17, 19)
            X3 = X3.reshape(2, 8, 12, 5, 17, 17, 19)
            params = (aero_type, water, AOT, al, sza, vza, raa)

        # Perform interpolation on the LUT data.
        fn1 = RegularGridInterpolator(params, X1, bounds_error=False, fill_value=np.nan)
        fn2 = RegularGridInterpolator(params, X2, bounds_error=False, fill_value=np.nan)
        fn3 = RegularGridInterpolator(params, X3, bounds_error=False, fill_value=np.nan)

        return fn1, fn2, fn3
    

class AHI_angle:
    """
    This class is used to read auxiliary data for the AHI satellite, such as the solar zenith angle (SZA) and solar azimuth angle (SAA).
    """
    def __init__(self, date, col_AHI):
        """
        Constructor for the AHIAngle class.

        Args:
            date (str): The date in the format of 'yyyymmdd'.
            col_AHI (int): The number of columns in the AHI image.
        """
        self.sza_filename = f"{SZA_PATH}AHI_SZA_2018{date[4:11]}5.dat"
        self.saa_filename = f"{SAA_PATH}AHI_SAA_2018{date[4:11]}5.dat"
        self.col_AHI = col_AHI

    def _read_solar_angle(self, filename):
        """
        Reads the solar angle data from a file and resizes it to match the AHI image.

        Args:
            filename (str): The file path to the solar angle data.

        Returns:
            The solar angle data, with the same dimensions as the AHI image.
        """
        sa = np.memmap(filename, dtype='u2', mode='r', shape=(3000, 3000)) / 100
        sa = cv2.resize(np.array(sa, dtype='float64'), (self.col_AHI, self.col_AHI), interpolation=cv2.INTER_NEAREST)
        return sa

    def read_solar_angle(self):
        """
        Reads the SZA and SAA data concurrently using multiple threads.

        Returns:
            A list containing the SZA and SAA data, each with the same dimensions as the AHI image.
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            file_list = [self.sza_filename, self.saa_filename]
            results = [executor.submit(self._read_solar_angle, file) for file in file_list]
        result_list = [result.result() for result in results]
        return result_list
    

class CAMS_data:
    def __init__(self, Y, M, D, H, MI, lat, lon, row):
        """
        Constructor for the CAMS_data class.

        Args:
            Y (str): The year in the format of 'yyyy'.
            M (str): The month in the format of 'mm'.
            D (str): The day in the format of 'dd'.
            H (str): The hour in the format of 'hh'.
            MI (str): The minute in the format of 'mm'.
            lat (float): The latitude of the location.
            lon (float): The longitude of the location.
            row (int): The number of rows in the output data.
        """
        self.YYYY = Y
        self.MM = M
        self.DD = D
        self.HH = H
        self.MIN = MI
        self.lon = lon
        self.lat = lat
        self.row = row

    def read_CAMS(self):
        """
        Reads CAMS atmospheric data.

        Returns:
            Ozone, water vapor, and aerosol optical thickness data.
        """
        # Determine which files to read based on the hour of the observation
        if int(self.HH) >= 21:
            d1 = dt.datetime(int(self.YYYY), int(self.MM), int(self.DD))
            d2 = dt.datetime(int(self.YYYY), int(self.MM), int(self.DD)) + dt.timedelta(days=1)

            ds1 = xr.open_dataset(CAMS_PATH + d1.strftime('%Y') + d1.strftime('%m') + d1.strftime('%d') + '.nc')
            ds2 = xr.open_dataset(CAMS_PATH + d2.strftime('%Y') + d2.strftime('%m') + d2.strftime('%d') + '.nc')
            ds = xr.merge([ds1, ds2])

        else:
            ds = xr.open_dataset(CAMS_PATH + self.YYYY + self.MM + self.DD + '.nc')

        # Interpolate data to the specified location and time
        dtime = dt.datetime(int(self.YYYY), int(self.MM), int(self.DD), int(self.HH), int(self.MIN) + 5)
        ds = ds.interp(time=dtime, method='linear')
        ds = ds.interp(longitude=self.lon, latitude=self.lat, method="linear")

        # Extract data from the dataset
        OZ = ds['gtco3'].values
        WV = ds['tcwv'].values
        AOT550 = ds['aod550'].values

        # Convert the units of ozone and water vapor
        WV = WV / 10
        OZ = OZ * 46.6975764

        # Adjust the range of the data to match the reference range
        OZ = np.clip(OZ, min(ozone), max(ozone))
        WV = np.clip(WV, min(water), max(water))
        AOT550 = np.clip(AOT550, min(AOT), max(AOT))

        return OZ,WV,AOT550
    
    def read_CAMS_AERO(self):
        """
        Reads CAMS aerosol data.

        Returns:
            A binary array indicating the dominant type of aerosol at the location and time.
        """
        # Determine which files to read based on the hour of the observation
        if int(self.HH) >= 21:
            d1 = dt.datetime(int(self.YYYY), int(self.MM), int(self.DD))
            d2 = dt.datetime(int(self.YYYY), int(self.MM), int(self.DD)) + dt.timedelta(days=1)

            ds1 = xr.open_dataset(CAMS_AERO_PATH + d1.strftime('%Y') + d1.strftime('%m') + d1.strftime('%d') + '.nc')
            ds2 = xr.open_dataset(CAMS_AERO_PATH + d2.strftime('%Y') + d2.strftime('%m') + d2.strftime('%d') + '.nc')
            ds = xr.merge([ds1, ds2])

        else:
            ds = xr.open_dataset(CAMS_AERO_PATH + self.YYYY + self.MM + self.DD + '.nc')

        # Interpolate data to the specified location and time
        dtime = dt.datetime(int(self.YYYY), int(self.MM), int(self.DD), int(self.HH), int(self.MIN) + 5)
        ds_interp = ds.interp(time=dtime, method='linear')
        ds_interp = ds_interp.interp(longitude=self.lon, latitude=self.lat, method="linear")
        max_percent = np.amax([ds_interp['duaod550'].values, ds_interp['suaod550'].values, ds_interp['bcaod550'].values, ds_interp['omaod550'].values, ds_interp['ssaod550'].values], axis=0)
        Aerosol_type = np.where(ds_interp['ssaod550'].values == max_percent, 1, 0)

        return Aerosol_type

    
def copy_chunk(source_path, dest_path, start_byte, end_byte):
    with open(source_path, 'rb') as source:
        source.seek(start_byte)
        data = source.read(end_byte - start_byte + 1)
        
        with open(dest_path, 'r+b') as dest:
            dest.seek(start_byte)
            dest.write(data)

def multi_threaded_copy(source_path, dest_path, num_threads):
    # 确定文件大小和每个线程应该复制的字节
    file_size = os.path.getsize(source_path)
    bytes_per_thread = file_size // num_threads
    threads = []

    # 创建目标文件并预先分配空间
    with open(dest_path, 'wb') as f:
        f.write(b'\0' * file_size)

    for i in range(num_threads):
        start_byte = i * bytes_per_thread
        # 最后一个线程复制剩余的所有字节
        end_byte = start_byte + bytes_per_thread - 1 if i != num_threads - 1 else file_size - 1
        thread = threading.Thread(target=copy_chunk, args=(source_path, dest_path, start_byte, end_byte))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    print("Copy completed!")



def decompression(local_file_path):
    p = subprocess.Popen("lbzip2 -d {}".format(local_file_path), shell=True)
    p.communicate()
    
    
    
def H8_Process(ACCOUNT, PW, Band, Band_number, Date,Savepath):
    H8 = H8_data(ACCOUNT, PW, Band, Band_number, Date,Savepath)
    return H8.file_path(),H8.get_filename()

def mkdir(path):
    os.makedirs(path, exist_ok=True)

def remove_original_file(path):
    shutil.rmtree(path)


def Time_split(time):
    date = time.strftime("%Y%m%d%H%M")
    YYYY, MM, DD, HH, MIN = date[0:4], date[4:6], date[6:8], date[8:10], date[10:12]
    return YYYY,MM,DD,HH,MIN,date

def read_Landmask(res):
    if res == 0.005:
        LAND_MASK_PATH = '/data01/GEO/INPUT/LAND_MASK/Landmask_05.dat'
        col = 24000
    elif res == 0.01:
        LAND_MASK_PATH = '/data01/GEO/INPUT/LAND_MASK/Landmask_10.dat' 
        col = 12000
    elif res == 0.02:
        LAND_MASK_PATH = '/data01/GEO/INPUT/LAND_MASK/Landmask_20.dat'
        col = 6000

    with open(LAND_MASK_PATH,'rb') as fp:
        LM = np.frombuffer(fp.read(),dtype='u1').reshape(col,col).astype('bool')
    return LM   


def read_cams_data(CAMS_data_obj):
    """Reads aerosol optical depth, water vapor, and ozone data from a CAMS data object using multithreading.

    Args:
        CAMS_data_obj (object): Object containing CAMS data.

    Returns:
        tuple: A tuple containing the aerosol type, ozone, water vapor, and AOT550 values.
    """
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_aero = executor.submit(CAMS_data_obj.read_CAMS_AERO)
        future_cams = executor.submit(CAMS_data_obj.read_CAMS)
    Aerosol_type = future_aero.result()
    OZ, WV, AOT550 = future_cams.result()
    return Aerosol_type, OZ, WV, AOT550


@nb.jit()
def get_water_idx(Landmask):
    """Creates a list of water index values based on a landmask input.

    Args:
        Landmask (array): 2D array of boolean values indicating land or water.

    Returns:
        list: List of water index values.
    """
    Water_idx = []
    for i in range(Landmask.shape[0]):
        line_idx =[]
        for j in range(Landmask.shape[1]):
            if Landmask[i,j] == True:
                line_idx.append(j)

        Water_idx.append(line_idx)
    return Water_idx


def calculate_6s_band1(fn1_1, fn2_1, fn3_1, Landmask, Aerosol_type, OZ, AOT550, RAA, AHI_SZA, AHI_VZA, AHI_AL, AHI_data, i):
    """Calculate surface reflectance for Band 1 using 6S model.
    
    Args:
        fn1_1 (function): Function for the first component of the aerosol model.
        fn2_1 (function): Function for the second component of the aerosol model.
        fn3_1 (function): Function for the third component of the aerosol model.
        Landmask (2D numpy array): Landmask for the region of interest.
        Aerosol_type (2D numpy array): Aerosol type data for the region of interest.
        OZ (2D numpy array): Ozone data for the region of interest.
        AOT550 (2D numpy array): Aerosol optical thickness data for the region of interest.
        RAA (2D numpy array): Relative azimuth angle data for the region of interest.
        AHI_SZA (2D numpy array): Satellite zenith angle data for the region of interest.
        AHI_VZA (2D numpy array): View zenith angle data for the region of interest.
        AHI_AL (2D numpy array): Absolute difference of satellite and view azimuth angle data for the region of interest.
        AHI_data (2D numpy array): Satellite data for the region of interest.
        i (int): Index for the current time step.
        
    Returns:
        SR (1D numpy array): Surface reflectance for Band 1.
    """
    Aero_input = Aerosol_type[i][Landmask[i]]
    OZ_input = OZ[i][Landmask[i]]
    AOT550_input = AOT550[i][Landmask[i]]
    RAA_input = RAA[i][Landmask[i]]
    SZA_input = AHI_SZA[i][Landmask[i]]
    VZA_input = AHI_VZA[i][Landmask[i]]
    AL_input = AHI_AL[i][Landmask[i]]
    AHI_data_input = AHI_data[i][Landmask[i]]

    # Prepare input data for the 6S model
    xi = np.array([Aero_input, OZ_input, AOT550_input, AL_input, SZA_input, VZA_input, RAA_input]).T
    
    # Calculate the first, second, and third components of the aerosol model
    xa = fn1_1(xi)
    xb = fn2_1(xi)
    xc = fn3_1(xi)
    
    # Calculate surface reflectance
    y = xa * AHI_data_input - xb
    SR = y / (1 + xc * y)
    
    return SR

def calculate_6s_band2(fn1_2, fn2_2, fn3_2,Landmask,Aerosol_type,OZ,AOT550,RAA,AHI_SZA,AHI_VZA,AHI_AL,AHI_data,i):
    
    Aero_input = Aerosol_type[i][Landmask[i]]
    OZ_input = OZ[i][Landmask[i]]
    AOT550_input = AOT550[i][Landmask[i]]
    RAA_input = RAA[i][Landmask[i]]
    SZA_input = AHI_SZA[i][Landmask[i]]
    VZA_input = AHI_VZA[i][Landmask[i]]
    AL_input = AHI_AL[i][Landmask[i]]
    AHI_data_input = AHI_data[i][Landmask[i]]

    xi = np.array([Aero_input,OZ_input,AOT550_input,AL_input,SZA_input,VZA_input,RAA_input])
    xi = xi.T
    xa = fn1_2(xi)
    xb = fn2_2(xi)
    xc = fn3_2(xi)
    y = xa*AHI_data_input-xb
    SR = y/(1+xc*y)
    return SR


def calculate_6s_band3(fn1_3, fn2_3, fn3_3,Landmask,Aerosol_type,WV,OZ,AOT550,RAA,AHI_SZA,AHI_VZA,AHI_AL,AHI_data,i):
    
    Aero_input = Aerosol_type[i][Landmask[i]]
    WV_input = WV[i][Landmask[i]]
    OZ_input = OZ[i][Landmask[i]]
    AOT550_input = AOT550[i][Landmask[i]]
    RAA_input = RAA[i][Landmask[i]]
    SZA_input = AHI_SZA[i][Landmask[i]]
    VZA_input = AHI_VZA[i][Landmask[i]]
    AL_input = AHI_AL[i][Landmask[i]]
    AHI_data_input = AHI_data[i][Landmask[i]]

    xi = np.array([Aero_input,WV_input,OZ_input,AOT550_input,AL_input,SZA_input,VZA_input,RAA_input])
    xi = xi.T
    xa = fn1_3(xi)
    xb = fn2_3(xi)
    xc = fn3_3(xi)
    y = xa*AHI_data_input-xb
    SR = y/(1+xc*y)
    return SR 

def calculate_6s_band4(fn1_4, fn2_4, fn3_4,Landmask,Aerosol_type,WV,AOT550,RAA,AHI_SZA,AHI_VZA,AHI_AL,AHI_data,i):

    Aero_input = Aerosol_type[i][Landmask[i]]
    WV_input = WV[i][Landmask[i]]
    AOT550_input = AOT550[i][Landmask[i]]
    RAA_input = RAA[i][Landmask[i]]
    SZA_input = AHI_SZA[i][Landmask[i]]
    VZA_input = AHI_VZA[i][Landmask[i]]
    AL_input = AHI_AL[i][Landmask[i]]
    AHI_data_input = AHI_data[i][Landmask[i]]

    xi = np.array([Aero_input,WV_input,AOT550_input,AL_input,SZA_input,VZA_input,RAA_input])
    xi = xi.T
    xa = fn1_4(xi)
    xb = fn2_4(xi)
    xc = fn3_4(xi)
    y = xa*AHI_data_input-xb
    SR = y/(1+xc*y)
    return SR    

def calculate_6s_band5(fn1_4, fn2_4, fn3_4,Landmask,Aerosol_type,WV,AOT550,RAA,AHI_SZA,AHI_VZA,AHI_AL,AHI_data,i):

    Aero_input = Aerosol_type[i][Landmask[i]]
    WV_input = WV[i][Landmask[i]]
    AOT550_input = AOT550[i][Landmask[i]]
    RAA_input = RAA[i][Landmask[i]]
    SZA_input = AHI_SZA[i][Landmask[i]]
    VZA_input = AHI_VZA[i][Landmask[i]]
    AL_input = AHI_AL[i][Landmask[i]]
    AHI_data_input = AHI_data[i][Landmask[i]]

    xi = np.array([Aero_input,WV_input,AOT550_input,AL_input,SZA_input,VZA_input,RAA_input])
    xi = xi.T
    xa = fn1_4(xi)
    xb = fn2_4(xi)
    xc = fn3_4(xi)
    y = xa*AHI_data_input-xb
    SR = y/(1+xc*y)
    return SR  

def calculate_6s_band6(fn1_4, fn2_4, fn3_4,Landmask,Aerosol_type,WV,AOT550,RAA,AHI_SZA,AHI_VZA,AHI_AL,AHI_data,i):

    Aero_input = Aerosol_type[i][Landmask[i]]
    WV_input = WV[i][Landmask[i]]
    AOT550_input = AOT550[i][Landmask[i]]
    RAA_input = RAA[i][Landmask[i]]
    SZA_input = AHI_SZA[i][Landmask[i]]
    VZA_input = AHI_VZA[i][Landmask[i]]
    AL_input = AHI_AL[i][Landmask[i]]
    AHI_data_input = AHI_data[i][Landmask[i]]

    xi = np.array([Aero_input,WV_input,AOT550_input,AL_input,SZA_input,VZA_input,RAA_input])
    xi = xi.T
    xa = fn1_4(xi)
    xb = fn2_4(xi)
    xc = fn3_4(xi)
    y = xa*AHI_data_input-xb
    SR = y/(1+xc*y)
    return SR  

def main_read(res,lat_up, lat_bottom,lon_left, lon_right):
    
    # Calculate rows and columns
    row_AHI = round((lat_up - lat_bottom) / res)
    col_AHI = round((lon_right - lon_left) / res)

    # Longitude and latitude grid
    AHI_lat = np.linspace(lat_up - res / 2, lat_bottom + res / 2, row_AHI)
    AHI_lon = np.linspace(lon_left + res / 2, lon_right - res / 2, col_AHI)
    
    
    row = round((60 - lat_up) / res)
    col = round((lon_left - 85) / res)

    # Read AHI VZA, VAA, AHI, and Landmask by resolution
    AHI_VZA, AHI_VAA = read_AHI_VA(res)
    Landmask = read_Landmask(res)
    AHI_AL = read_AHI_AL(res)
    Water_idx = get_water_idx(Landmask[row:row+row_AHI,col:col+col_AHI])
    
    return row,col,row_AHI,col_AHI,AHI_lat,AHI_lon,AHI_VZA[row:row+row_AHI,col:col+col_AHI], AHI_VAA[row:row+row_AHI,col:col+col_AHI],AHI_AL[row:row+row_AHI,col:col+col_AHI],Water_idx,Landmask[row:row+row_AHI,col:col+col_AHI]