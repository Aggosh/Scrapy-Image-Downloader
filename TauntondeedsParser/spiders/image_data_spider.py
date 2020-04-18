import scrapy
import urllib.parse
import re
import datetime


class ImageDataBase(scrapy.Spider):
    @classmethod
    def search_url(cls):
        return "http://www.tauntondeeds.com/Searches/ImageSearch.aspx"

    custom_settings = {
        'ITEM_PIPELINES': {
            'TauntondeedsParser.pipelines.TauntondeedsparserPipeline': 300
        }
    }


class ImageDataSpider(ImageDataBase):
    name = 'image_data'

    start_urls = [
        ImageDataBase.search_url()
    ]

    def parse(self, response):
        parser = ImageDataParser()

        form_data = parser.create_form_data(response, 0)

        yield scrapy.FormRequest(
            ImageDataBase.search_url(),
            formdata=form_data,
            callback=parser.search_documents
        )


class ImageDataParser:
    DEED = '101627'

    def search_documents(self, response) -> dict:
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

                date = self._add_none(cols[1].css('::text').get())
                type_ = self._add_none(cols[2].css('::text').get())
                book = self._add_none(cols[3].css('::text').get())
                page_num = self._add_none(cols[4].css('::text').get())
                doc_num = self._add_none(cols[5].css('::text').get())
                city = self._add_none(cols[6].css('::text').get())
                description = self._add_none(cols[7].css('span::text').get())
                cost = self.get_cost(description)
                street_address = self.get_street(description)
                state = self._state(city)
                zip_ = self.get_zip(description)

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

    def parse_input_form_data(self, response) -> dict:
        part_form_data = {}
        for input_ in response.css('input'):
            value = input_.css('::attr(value)').get()

            if value is None:
                value = ''

            part_form_data.update({
                input_.css('::attr(name)').get(): value
            })

        return part_form_data

    def parse_script_form_data(self, response) -> dict:
        part_form_data = {}
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
                part_form_data.update(
                    {'ctl00_rsmScriptManager_HiddenField': param})
                break

        return part_form_data

    def edit_and_add_additional_form_data(self, page: int, form_data: dict) -> dict:
        START_TIME_1 = '2020-01-01'
        START_TIME_2 = '01/01/2020'
        START_TIME_3 = '2020-01-01-00-00-00'

        today_date = datetime.date.today()
        END_TIME_1 = datetime.datetime.strftime(today_date, '%Y-%m-%d')
        END_TIME_2 = datetime.datetime.strftime(today_date, '%m/%d/%Y')
        END_TIME_3 = datetime.datetime.strftime(
            today_date, '%Y-%m-%d-00-00-00')

        if page > 1:
            form_data.update({'__EVENTTARGET':
                              'ctl00$cphMainContent$gvSearchResults',
                              '__EVENTARGUMENT': 'Page${}'.format(page)})
            try:
                del form_data['ctl00$cphMainContent$btnSearchLC']
            except KeyError:
                pass
        else:
            form_data.update({'__EVENTTARGET': '',
                              '__EVENTARGUMENT': ''})

        form_data.update({'ctl00$cphMainCon' +
                          'tent$ddlLCDocumentType$vddlDropDown':
                          self.DEED,
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

    def create_form_data(self, response, page: int) -> dict:
        form_data = {}
        form_data.update(self.parse_input_form_data(response))
        form_data.update(self.parse_script_form_data(response))

        self.edit_and_add_additional_form_data(page, form_data)

        return form_data

    def _state(self, city: str):
        # edit for different site
        return 'Massachusetts'

    def get_cost(self, description: str) -> str:
        try:
            cost = float(description.split(',')[-1].replace(' $', ''))
        except ValueError:
            cost = None

        return cost

    def get_zip(self, description: str) -> str:
        result = re.match(r'(^\d{5}$)|(^\d{9}$)|(^\d{5}-\d{4}$)', description)
        if result is None:
            return result
        else:
            return result.group(0)

    def get_street(self, description: str) -> str:
        start = description.find('-')+3  # 3 is len of '-G '
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
        # get len grid of pages
        try:
            page_count = len(response.css(
                'table#ctl00_cphMainContent_gvSearchResults tr.gridPager tr'
            )[0].css('td').getall())
        except (ValueError, KeyError, StopIteration):
            page_count = 0

        return page_count

    def _try_del_form_data(self, form_data: dict, key: str) -> dict:
        try:
            del form_data[key]
        except KeyError:
            pass

        return form_data
