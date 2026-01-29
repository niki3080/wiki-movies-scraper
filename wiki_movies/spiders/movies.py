import scrapy
import re


# функция очистки текста
def clean_text(s):
    if not s:
        return ""

    s = re.sub(r"\[\d+\]", "", s)   # удаляем сноски
    s = re.sub(r"\s+", " ", s)      # пробелы
    return s.strip(" ,")            # крайние запятые


class MoviesSpider(scrapy.Spider):
    name = "movies"
    allowed_domains = ["ru.wikipedia.org"]
    start_urls = ["https://ru.wikipedia.org/wiki/Категория:Фильмы_по_алфавиту"]


    # соответствие итоговых полей возможным названиям в infobox
    FIELD_MAP = {
        "genre": ["Жанр", "Жанры"],
        "director": ["Режиссёр", "Режиссёры"],
        "country": ["Страна", "Страны"],
        "year": ["Год", "Дата выхода", "Первый показ"]
    }

    # парсинг страниц: переход по фильмам и на следующую страницу
    def parse(self, response):
        links = response.css("div.mw-category-columns ul li a::attr(href)").getall()
        for link in links:
            yield response.follow(link, callback=self.parse_movie)

        next_page = response.xpath("//a[contains(text(), 'Следующая страница')]/@href").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_movie(self, response):
        
        # все строки infobox собираются в словарь
        info_data = {}
        rows = response.xpath("//table[contains(@class, 'infobox')]//tr")
        
        for row in rows:
            label = row.xpath("./th//text()").get()
            if label:
                label = label.strip().rstrip(':')
                
                # извлечение текста из ячеек
                raw_values = row.xpath("./td//text()[not(ancestor::sup) and not(ancestor::style)]").getall()
                
                cleaned_chunks = [
                    clean_text(v) 
                    for v in raw_values 
                    if clean_text(v) and any(char.isalnum() for char in clean_text(v))
                ]
                
                # соединяем текст через запятую
                info_data[label] = ", ".join(cleaned_chunks)

        # итоговая запись о фильме
        item = {"title": response.xpath("//h1[@id='firstHeading']//text()").get()}

        for field, labels in self.FIELD_MAP.items():
            value = next((info_data[l] for l in labels if l in info_data), None)
            
            # для года оставляем только сам год, без даты и месяца
            if field == "year" and value:
                match = re.search(r"\b(18|19|20)\d{2}\b", value)
                value = match.group(0) if match else None
            
            item[field] = value

        yield item