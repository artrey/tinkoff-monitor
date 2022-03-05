import datetime
import decimal
import re
import time
from dataclasses import dataclass
from functools import partial
from typing import Any

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options


@dataclass
class AtmInfo:
    rub: int
    usd: int
    eur: int


options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-gpu")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=920,800")


def cast_or_def(val: Any, caster: callable, default: Any) -> Any:
    if val:
        return caster(val)
    return default


to_int_or_zero = partial(cast_or_def, lambda x: x[0][:-1], 0)


def get_info(lat: decimal.Decimal, lon: decimal.Decimal) -> AtmInfo:
    coords = f"latitude={lat}&longitude={lon}"
    rub, usd, eur = 0, 0, 0

    driver = webdriver.Chrome(options=options)
    try:
        driver.implicitly_wait(10)
        driver.get(f"https://www.tinkoff.ru/maps/atm/?{coords}&zoom=18&partner=tcs&currency=RUB&amount=")

        map = driver.find_element(value="mapComponent")
        ac = ActionChains(driver)
        ac.move_to_element(map).click().perform()
        time.sleep(0.5)
        soup = BeautifulSoup(driver.page_source, features="html.parser")
        message = soup.find("div", text="Сейчас в банкомате").next_sibling.text.strip()

        letters = re.sub(r"\s+", "", message, flags=re.UNICODE)
        rub = to_int_or_zero(re.findall(r"\d+₽", letters))
        usd = to_int_or_zero(re.findall(r"\d+\$", letters))
        eur = to_int_or_zero(re.findall(r"\d+€", letters))

    except Exception as ex:
        print(datetime.datetime.now().isoformat(), "ERROR", coords, ex, sep=" | ")
    finally:
        driver.quit()
        time.sleep(1)

    return AtmInfo(rub=rub, usd=usd, eur=eur)
