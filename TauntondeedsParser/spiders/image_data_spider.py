import scrapy
import urllib.parse
import requests

from datetime import datetime
from ..items import TauntondeedsparserItem


class ImageDataSpider(scrapy.Spider):
    name = 'image_data'

    start_urls = [
        'http://www.tauntondeeds.com/Searches/ImageSearch.aspx'
    ]

    def parse(self, response):

        form_data = self.create_form_data(response, 0)

        yield scrapy.FormRequest(
            'http://www.tauntondeeds.com/Searches/ImageSearch.aspx',
            formdata=form_data,
            callback=self.main_parser
        )

    def main_parser(self, response) -> dict:
        pages = self.get_page_count(response)

        for page in range(1, pages+1):
            form_data = self.create_form_data(response, page)
            yield scrapy.FormRequest(
                'http://www.tauntondeeds.com/Searches/ImageSearch.aspx',
                formdata=form_data,
                callback=self.result_parser
            )

    def result_parser(self, response) -> dict:
        table = response.css('table#ctl00_cphMainContent_gvSearchResults')
        for row in table.css('tr'):
            class_row = row.css('::attr(class)').get()
            if class_row == 'gridAltRow' or class_row == 'gridRow':
                cols = row.css('td')

                row_date = self._add_none(cols[1].css('::text').get())

                date = datetime.strptime(row_date, '%m/%d/%Y')
                type_ = self._add_none(cols[2].css('::text').get())
                book = self._add_none(cols[3].css('::text').get())
                page_num = self._add_none(cols[4].css('::text').get())
                doc_num = self._add_none(cols[5].css('::text').get())
                city = self._add_none(cols[6].css('::text').get())
                description = self._add_none(cols[7].css('span::text').get())
                cost = self.get_cost(description)
                street_address = self.get_street(description)
                state = self.get_state(city)
                zip_ = self.get_zip(state, city)

                yield {
                    'date': date,
                    'type': type_,
                    'book': book,
                    'page_num': page_num,
                    'doc_num': doc_num,
                    'city': city,
                    'description': description,
                    'cost': cost,
                    'street_address': street_address,
                    'state': state,
                    'zip': zip_,
                }

            else:
                continue

    def parse_input_form_data(self, response, form_data: dict) -> dict:
        for input_ in response.css('input'):
            value = input_.css('::attr(value)').get()

            if value is None:
                value = ''

            form_data.update({
                input_.css('::attr(name)').get(): value
            })

        return form_data

    def parse_script_form_data(self, response, form_data: dict) -> dict:
        for script in response.css('script'):
            script_src = script.css('::attr(src)').get()
            if (script_src is not None
                    and 'Telerik.Web.UI.WebResource.axd' in script_src):

                param = urllib.parse.unquote_plus(script_src)

                unnecessary_str = '/Telerik.Web.UI.WebResource.axd?' + \
                    '_TSM_HiddenField_=' + \
                    'ctl00_rsmScriptManager_HiddenField&' + \
                    'compress=1&_TSM_CombinedScripts_='

                param = param.replace(unnecessary_str, '')
                form_data.update(
                    {'ctl00_rsmScriptManager_HiddenField': param})
                break

        return form_data

    def add_additional_form_data(self, form_data: dict, page: int) -> dict:
        DEED = '101627'

        START_TIME_1 = '2020-01-01'
        START_TIME_2 = '01/01/2020'
        START_TIME_3 = '2020-01-01-00-00-00'

        END_TIME_1 = '2020-12-31'
        END_TIME_2 = '12/31/2020'
        END_TIME_3 = '2020-12-31-00-00-00'

        if page > 1:
            form_data.update({'__EVENTTARGET':
                              'ctl00$cphMainContent$gvSearchResults',
                              '__EVENTARGUMENT': f'Page${page}'})
            del form_data['ctl00$cphMainContent$btnSearchLC']
        else:
            form_data.update({'__EVENTTARGET': '',
                              '__EVENTARGUMENT': ''})

        form_data.update({'ctl00$cphMainCon' +
                          'tent$ddlLCDocumentType$vddlDropDown':
                          DEED,
                          'ctl00$cphMainContent$txtLCSTartDate':
                          START_TIME_1,
                          'ctl00_cphMainContent_txtLCSTartDate_dateInput_text':
                          START_TIME_2,
                          'ctl00$cphMainContent$txtLCSTartDate$dateInput':
                          START_TIME_3,
                          'ctl00$cphMainContent$txtLCEndDate': END_TIME_1,
                          'ctl00_cphMainContent_txtLCEndDate_dateInput_text':
                          END_TIME_2,
                          'ctl00$cphMainContent$txtLCEndDate$dateInput':
                          END_TIME_3,
                          'ctl00_cphMainContent_txtRLStar' +
                          'tDate_dateInput_ClientState':
                          {"enabled": True, "emptyMessage": "",
                              "minDateStr": "1/1/1900 0:0:0",
                           "maxDateStr": "12/31/2099 0:0:0"}
                          })

        form_data = self._try_del_form_data(
            form_data, 'ctl00$cphMainContent$btnPrint')
        form_data = self._try_del_form_data(
            form_data, 'ctl00$cphMainContent$btnSearchPlan')
        form_data = self._try_del_form_data(
            form_data, 'ctl00$cphMainContent$btnSearchRL')

        return form_data

    def create_form_data(self, response, page: int) -> dict:
        form_data = {}
        form_data = self.parse_input_form_data(response, form_data)
        form_data = self.parse_script_form_data(response, form_data)
        form_data = self.add_additional_form_data(form_data, page)
        return form_data

    def get_state(self, city: str):
        url = f'https://nominatim.openstreetmap.org/search?' + \
            'city={city}&format=json&addressdetails=1&accept-language=eng'
        response = requests.get(url)
        return response.json()[0].get('address').get('state')

    def get_cost(self, description: str) -> str:
        try:
            cost = float(description.split(',')[-1].replace(' $', ''))
        except ValueError:
            cost = None

        return cost

    def get_zip(self, state: str, city: str) -> str:
        API = 'BhJUvvdtu1Eqtrywt9wpK5frtc423x4PoZ8SU6kXMeCY6efrNLyxy1LsBdHm3EWQ'
        url = f'https://www.zipcodeapi.com/rest/{API}/city-zips.json/{city}/{state}'
        response = requests.get(url)
        try:
            return response.json().get('zip_codes')[0]
        except (KeyError, IndexError):
            return None

    def get_street(self, description: str) -> str:
        start = description.find('-')+3
        if start == 2:
            start = 0
        end = description.find(',', start)
        street_address = description[start:end]
        if street_address == '':
            return None
        else:
            return street_address

    def _add_none(self, param: str) -> str or None:
        if len(param) < 2:
            return None
        else:
            return param

    def get_page_count(self, response):
        # get grid of pages
        page_count = len(response.css(
            'table#ctl00_cphMainContent_gvSearchResults tr.gridPager tr'
        )[0].css('td').getall())
        return page_count

    def _try_del_form_data(self, form_data: dict, key: str) -> dict:
        try:
            del form_data[key]
        except KeyError:
            pass

        return form_data
