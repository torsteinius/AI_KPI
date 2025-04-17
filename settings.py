class Settings:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Settings, cls).__new__(cls)
            cls._instance.__initialize()
        return cls._instance

    def __initialize(self):
        self.__read_files_csv = "operation/read_files.csv"
        self.__pdf_root = "pdf/tickers"
        self.__jpeg_root = "jpeg/tickers"
        self.__data_root = "data"

    @property
    def read_files_csv(self):
        return self.__read_files_csv

    @property
    def pdf_root(self):
        return self.__pdf_root
    
    @property
    def jpeg_root(self):
        return self.__jpeg_root
    
    @property
    def data_root(self):
        return self.__data_root
    


# Usage
settings1 = Settings()
settings2 = Settings()

print(settings1 is settings2)  # True
print(settings1.read_files_csv)  # operation/read_files.csv

