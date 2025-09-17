
import requests
import pandas as pd
from bs4 import BeautifulSoup


########################################################################
#
# It currently extracts the first table it finds.
# It handles both cases where headers are defined with <th> or using the first row’s <td>.
# It skips empty rows.
# If the table has merged cells (rowspan/colspan), further handling is required.
#
########################################################################

class WebPageTableDataExtractor:
    def __init__(self, url):
        self.url = url
        
        # Create a file-name from the URL-name
        self.file_name = url.replace("http://", "").replace("https://", "").replace("/", "_") + ".csv"

        # If file name exists, read data-frame from it - else extract from web page
        try:
            self.dataframe = pd.read_csv(self.file_name)
            print(f"DataFrame loaded from {self.file_name}")
        except FileNotFoundError:
            self.dataframe = self._extract_table()
            self.dataframe.to_csv(self.file_name, index=False)


    def getFileNameForDataFrame(self):
        return self.file_name

    def _extract_table(self):
        # Download the web page content
        response = requests.get(self.url)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch URL: {self.url}")
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the first table
        table = soup.find('table')
        if not table:
            raise Exception("No table found in the page")

        print("Table found, extracting data...")

        # Extract headers
        headers = []
        header_row = table.find('tr')
        if header_row:
            th_tags = header_row.find_all('th')
            if th_tags:
                headers = [th.get_text(strip=True) for th in th_tags]
            else:
                # If no <th>, use first row's <td> as headers
                td_tags = header_row.find_all('td')
                headers = [td.get_text(strip=True) for td in td_tags]

        print(f"Headers found : {headers}")

        # Extract all rows
        rows = []
        for row in table.find_all('tr')[1:]:  # Skip header row
            cells = row.find_all(['td', 'th'])
            row_data = [cell.get_text(strip=True) for cell in cells]
            if row_data:
                rows.append(row_data)

        print(f"Total rows extracted : {len(rows)}")

        # Create DataFrame
        df = pd.DataFrame(rows, columns=headers if headers else None)
        return df

    def getDataFrame(self):
        return self.dataframe

