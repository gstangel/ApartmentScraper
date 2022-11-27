"""
This script was created to scrape apartments.com,
then export a spreadsheet containing the apartment information and
calculated travel time to a target destination using Google API services.
Useful for finding apt with reasonable travel distance to work when moving.
"""

from bs4 import BeautifulSoup
import requests
import pandas as pd
import googlemaps

# google api key
API_KEY = ""

# google maps client
gmaps = googlemaps.Client(key=API_KEY)

# Headers for http requests
HEADERS = {
    'User-Agent':
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36',
}


class Scraper:
    def __init__(self, state, city, target_address):
        self.state = state
        self.city = city
        self.target_address_coordinates = self.get_lat_long(target_address)  # where to calculate travel distance from

    def find_num_pages(self, first_page):
        """ determines the number of pages of listings available"""
        soup = BeautifulSoup(first_page.content, 'html.parser')

        page_range = soup.find(class_='pageRange')
        return int(page_range.text.split(' ')[-1])

    def get_all_pages(self):
        listing_pages = list()
        base_url = 'https://www.apartments.com/' + self.city + '-' + self.state + '/'
        first_page = requests.get(base_url, timeout=5, headers=HEADERS)  # get the first page
        listing_pages.append(first_page)
        num_pages = self.find_num_pages(first_page)
        for i in range(2, num_pages):
            print("Getting page {}".format(i))
            cur_page = base_url + str(i) + '/'
            listing_pages.append(requests.get(base_url, timeout=5, headers=HEADERS))

        return listing_pages

    def extract_apartment_data(self, listing_pages):
        """ extract apartments from the pages, calculate travel distance to target"""
        extracted_listings = list()

        for i, page in enumerate(listing_pages):
            print("Getting data for listings on page {}".format(i))
            soup = BeautifulSoup(page.content, 'html.parser')
            listings = soup.find_all(class_='placard placard-option-diamond has-header js-diamond')
            for listing in listings:
                cur_listing = {}
                cur_address = listing.find(class_="property-address js-url").text

                # get the travel time in seconds to specified destination
                travel_time = gmaps.distance_matrix(
                    self.get_lat_long(cur_address),
                    self.target_address_coordinates,
                    mode='driving')["rows"][0]["elements"][0]["duration"]["value"]
                travel_time = travel_time / 60  # convert to min

                # get rest of apartment data using beautifulsoup
                apt_price = listing.find(class_='property-pricing').text
                apt_name = listing.find(class_='js-placardTitle title').text
                apt_beds = listing.find(class_='property-beds').text
                apt_phone = listing.find(class_='phone-link js-phone')
                apt_link = listing.find(class_='property-link')['href']
                # add resulting data to dictionary
                cur_listing['apt_name'] = apt_name
                cur_listing['price'] = apt_price
                cur_listing['address'] = cur_address
                cur_listing['apt_beds'] = apt_beds
                cur_listing['travel_time'] = travel_time
                if apt_phone:
                    cur_listing['apt_phone'] = apt_phone.text
                cur_listing['apt_link'] = apt_link

                extracted_listings.append(cur_listing)
        return extracted_listings

    def export_to_excel(self, extracted_listings) -> None:
        """ export results to an excel file using pandas """
        df = pd.DataFrame(extracted_listings)
        df.to_excel("output.xlsx")

    def get_lat_long(self, address_or_zipcode) -> tuple:
        """ Gets Lat and Long from an address, used when calculating travel time"""
        lat, lng = None, None
        api_key = API_KEY
        base_url = "https://maps.googleapis.com/maps/api/geocode/json"
        endpoint = f"{base_url}?address={address_or_zipcode}&key={api_key}"
        # see how our endpoint includes our API key? Yes this is yet another reason to restrict the key
        r = requests.get(endpoint)
        if r.status_code not in range(200, 299):
            return None, None
        try:
            '''
            This try block incase any of our inputs are invalid. This is done instead
            of actually writing out handlers for all kinds of responses.
            '''
            results = r.json()['results'][0]
            lat = results['geometry']['location']['lat']
            lng = results['geometry']['location']['lng']
        except:
            pass
        return lat, lng

if __name__ == '__main__':
    scraper = Scraper(state='az', city='tucson', target_address="9000 S Rita Rd, Tucson, AZ 85747")
    pages = scraper.get_all_pages()
    extracted_listings = scraper.extract_apartment_data(pages)
    scraper.export_to_excel(extracted_listings)
