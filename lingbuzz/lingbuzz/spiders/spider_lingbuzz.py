import scrapy

class LingbuzzSpider(scrapy.Spider):
    name = 'lingbuzz_all'

    custom_settings = {
        "DOWNLOAD_DELAY": 3,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 3,
        "HTTPCACHE_ENABLED": True
    }

    
    start_urls = ['https://ling.auf.net/']

    def parse(self, response):
        hrefs =[]
        for href in response.xpath('//tr/td[4]/a/@href').extract():

            yield scrapy.Request(
                url= 'https://ling.auf.net/' + href,
                callback=self.parse_paper,
                meta={'url': response.xpath('//a[contains(text(), "[pdf]")]/@href').extract()}
            )

        next_url = 'https://ling.auf.net'+response.xpath('//a[contains(text(), "Next")]/@href').extract()[-1]

        yield scrapy.Request(url = next_url, callback=self.parse)


    def parse_paper(self, response):
        url = response.request.meta['url']
        title = response.xpath('//body/center//a/text()').extract()[0]
        authors = response.xpath('//body/center//a/text()').extract()[1:]
        abstract = response.xpath('//body/center//p/text()[3]')
        try: 
            published = response.xpath('//td[contains(text(), "Published in")]/following-sibling::td/text()').extract()
        except:
            published = 'None'
        keywords = response.xpath('//td[contains(text(), "keywords")]/following-sibling::td/text()').extract()

        yield {
        'title': title,
        'authors': authors,
        'published': published,
        'keywords': keywords,
        'abstract': abstract,
        'url': url
        }
