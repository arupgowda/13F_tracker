## 13F Fund Transactions tracker
The latest 2 fund transactions reported on Form 13F by a fund are pulled down from the SEC Edgar DB and tabulated into a spread sheet.
Once pulled down the results are analysed to see what securities were bought new, what were reduced and what were eliminated.

The code can be run in the following way:
```
Usage: #python scrape_fund_transactions.py <fund-name> <fund-CIK>
```
The fund-name is the name of the investment firm.
The fund-CIK is the unique no that is given to the fund by the SEC. This information can be determined by 
going to the SEC Edgar search and searching for the Investment fund.


This script can be run whenever there is a new transaction reported by tracking the RSS feed using the link:
```
rss_url = f"https://data.sec.gov/rss?cik={cik}&type=13F-HR,13F-HR/A&only=true&count=40" # noqa
```
Here CIK is the 10 digit CIK number assigned to the company.

Some sample investment funds CIK:
    - Scion Capital Management 1649339
    - Ensign Peak Advisors 1454984
    - Penn Davis McFarland 1108893
 
The script generates an output CSV called ```<fund_name>_<fund_ticker>.csv```
For example: penn_davis_mcfarland_1108893.csv

To understand the codes in the Forms 13F please look at the following SEC PDF linked here:
```
https://www.sec.gov/files/form13f.pdf
```
