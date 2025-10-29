import os
import sys
import feedparser
import logging
import json
import requests
import pandas as pd
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from collections import namedtuple

TGREEN = '\033[32m'  # Green Text
TRED = '\033[31m'    # Red Text
ENDC = '\033[m'      # reset to default

LOGGER = None

headers = {
    'User-Agent': 'sec_datascrape',
    'From': 'punyakotih@gmail.com',
}

xml_url = namedtuple('xml_url', ['reporting_date', 'url'])


# Analyse differences between the two filings
def analyse(filings):
    df1 = pd.DataFrame(filings[0])
    df2 = pd.DataFrame(filings[1])

    # First convert the numeric columns to appropriate types
    numeric_cols = ['value', 'shares']
    for col in numeric_cols:
        df1[col] = pd.to_numeric(df1[col], errors='coerce')
        df2[col] = pd.to_numeric(df2[col], errors='coerce')

    # Find common entries based on 'name' column
    common_names = set(df1['name']).intersection(set(df2['name']))

    # Find unique entries in DF1 and DF2
    df1_unique = df1[~df1['name'].isin(common_names)].copy()
    df2_unique = df2[~df2['name'].isin(common_names)].copy()

    # Process unique entries (set to 100% and 0%)
    df1_unique['shares_pct_change'] = 100.0
    df2_unique['shares_pct_change'] = -100.0

    # Filter both dataframes to only include common entries
    df1_common = df1[df1['name'].isin(common_names)]
    df2_common = df2[df2['name'].isin(common_names)]

    # Merge the dataframes to align the shares values
    common = pd.merge(
        df1_common,
        df2_common,
        on='name',
        suffixes=('_df1', '_df2')
    )

    # Calculate percentage change in shares
    common['shares_pct_change'] = (
        (common['shares_df1'] - common['shares_df2'])
        / common['shares_df2']) * 100
    common['shares_pct_change'] = common['shares_pct_change'].round(2)

    # Select only the columns we want from DF1
    common = common[[
        'name',
        'class_df1',
        'value_df1',
        'shares_df1',
        'type_df1',
        'shares_pct_change'
    ]]

    # Rename columns to remove the '_df1' suffix
    common.columns = [
        'name',
        'class',
        'value',
        'shares',
        'type',
        'shares_pct_change'
    ]

    resultList = [common, df1_unique, df2_unique]
    result = pd.concat(resultList)
    result = result.sort_values('shares_pct_change', ascending=False)
    result.to_csv(
        f"{fund_name}.csv",
        encoding='utf-8',
        index=False,
        header=True
    )


# Parse the XML tree
def parse_xml(xml_tree):
    root = ET.fromstring(xml_tree)
    holding_data = []
    # Define the namespace (found in the xmlns attribute)
    ns = {
        'ns': 'http://www.sec.gov/edgar/document/thirteenf/informationtable'
    }
    holdings = root.findall('.//ns:infoTable', namespaces=ns)
    LOGGER.info(f"Found {len(holdings)} holdings")
    for holding in holdings:
        data = {
            'name': holding.find('ns:nameOfIssuer', ns).text,
            'class': holding.find('ns:titleOfClass', ns).text,
            'value': holding.find('ns:value', ns).text,
            'shares': holding.find('ns:shrsOrPrnAmt/ns:sshPrnamt', ns).text,
            'type': holding.find('ns:shrsOrPrnAmt/ns:sshPrnamtType', ns).text,
        }
        holding_data.append(data)
    return holding_data


def process_xml_urls(xml_urls):
    filings = []
    # Process the last 2 filings
    for i in range(2):
        reporting_date, url = xml_urls[i]
        message = f"Processing XML: reporting date = {reporting_date}, url = {url}" # noqa
        print(message)
        LOGGER.info(message)
        r = requests.get(url, headers=headers)
        filings.append(parse_xml(r.content))
    return filings


def find_xml_href(filing_href):
    page = requests.get(filing_href, headers=headers).text
    soup = BeautifulSoup(page, 'html.parser')

    # Find the table containing the document links
    table = soup.find('table', {'class': 'tableFile'})

    xml_href = None

    # Iterate through the rows of the table to find the row with xml href
    for row in table.find_all('tr'):
        cells = row.find_all('td')
        if len(cells) > 4 and "INFORMATION TABLE" in cells[3].text:
            # Extract the href attribute from the <a> tag
            xml_href = cells[2].find('a')['href']
            if xml_href.endswith('.xml'):
                break

    LOGGER.info(f"filing_href = {filing_href}, xml_href = {xml_href}")
    return xml_href


# Process the RSS feed:
    # a) Pull out the filing href's
    # b) For each filing href request the page and find the filing xml href
    # c) Take the xml file name and craft the xml url link by appending the
    #    file name to the filing url base.
def process_rss_feed(feed):
    xml_urls = []
    for entry in feed.entries:
        filing_href = entry['filing-href']
        reporting_date = entry['report-date']
        LOGGER.info(f"reporting_date: {reporting_date}, filing_href = {filing_href}") # noqa

        filing_url = filing_href[:filing_href.rfind('/')]
        xml_file_path = find_xml_href(filing_href)
        xml_file_name = xml_file_path.split('/')[-1]
        url = os.path.join(filing_url, xml_file_name)
        xml_urls.append(xml_url(reporting_date, url))
    return xml_urls


# Get the RSS feed for this specific feed
def get_rss_feed(rss_url: str):
    LOGGER.info(f"RSS feed URL: {rss_url}")
    feed = feedparser.parse(rss_url, agent=json.dumps(headers))
    return feed


if __name__ == "__main__":
    if (len(sys.argv) == 1):
        print(TGREEN + 'Usage: #python ' + sys.argv[0] + ' <fund-name>' + ' <fund-CIK>', ENDC) # noqa
    else:
        global fund_name
        fund_name = sys.argv[1] + "_" + sys.argv[2]
        # Setup logging
        logging.basicConfig(filename=f'{fund_name}_fund_holdings.log',
                            format='%(levelname)s:%(message)s', # noqa
                            filemode='w',
                            level=logging.INFO)
        LOGGER = logging.getLogger()
        cik = sys.argv[2]
        if len(cik) != 10:
            # Use zfill to make it 10 digits by adding leading zeros
            cik = cik.zfill(10)
        # RSS URL
        rss_url = f"https://data.sec.gov/rss?cik={cik}&type=13F-HR,13F-HR/A&only=true&count=40" # noqa
        rss_feed = get_rss_feed(rss_url)
        xml_urls = process_rss_feed(rss_feed)
        filings = process_xml_urls(xml_urls)
        analyse(filings)
