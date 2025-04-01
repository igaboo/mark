class Listing():
    def __init__(self, url = None):
        self.title = None
        self.description = None
        self.price = None
        self.mileage = None
        self.location = None
        self.posted = None
        self.transmission = None
        self.image_url = None
        self.url = url
        
    def has_key_fields(self):
        # if all key fields are missing, this indicates an issue with the webpage
        return any([self.price, self.transmission, self.mileage, self.image_url])