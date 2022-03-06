import datetime
import decimal
import os.path
import re
import time
from dataclasses import dataclass
from functools import lru_cache, partial
from typing import Any, Optional

import cv2
import numpy as np
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


@dataclass
class AtmInfo:
    rub: int
    usd: int
    eur: int
    address: str
    worktime: str


options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-gpu")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=480,400")


def cast_or_def(val: Any, caster: callable, default: Any) -> Any:
    if val:
        return caster(val)
    return default


to_int_or_zero = partial(cast_or_def, caster=lambda x: int(x[0][:-1]), default=0)


@lru_cache(maxsize=None)
def get_pattern() -> np.array:
    return cv2.imread(os.path.join(os.path.dirname(__file__), "assets", "pattern.png"))


def find_coords(image: np.array) -> (int, int):
    method = cv2.TM_SQDIFF_NORMED

    pattern = get_pattern()
    # TODO: use mask of pattern
    result = cv2.matchTemplate(image, pattern, method)

    _, _, (x, y), _ = cv2.minMaxLoc(result)
    px, py = pattern.shape[:2]

    # cv2.rectangle(image, (x, y), (x + px, y + py), (255, 0, 0))
    # cv2.circle(image, (x + px // 2, y + py // 2), 5, (0, 0, 255))
    # cv2.imshow("demo", image)
    # cv2.waitKey(0)

    return x + px // 2, y + py // 2 + 30


def get_info(lat: decimal.Decimal, lon: decimal.Decimal) -> Optional[AtmInfo]:
    coords = f"latitude={lat}&longitude={lon}"

    driver = webdriver.Chrome(options=options)
    try:
        driver.implicitly_wait(10)
        driver.get(f"https://www.tinkoff.ru/maps/atm/?{coords}&zoom=18&partner=tcs&currency=RUB&amount=")

        map = (
            driver.find_element(value="mapComponent")
            .find_element(By.TAG_NAME, "ymaps")
            .find_element(By.TAG_NAME, "ymaps")
            .find_element(By.TAG_NAME, "ymaps")
            .find_element(By.TAG_NAME, "ymaps")
        )

        screenshot = cv2.imdecode(np.fromstring(map.screenshot_as_png, np.uint8), cv2.IMREAD_COLOR)
        x, y = find_coords(screenshot)

        ac = ActionChains(driver)
        ac.move_to_element_with_offset(map, x, y).click().perform()
        time.sleep(0.5)
        soup = BeautifulSoup(driver.page_source, features="html.parser")
        re_space_finder = re.compile(r"\s+", flags=re.UNICODE)

        money = soup.find("div", text="Сейчас в банкомате").next_sibling.text.strip()
        money_letters = re_space_finder.sub("", money)
        rub = to_int_or_zero(re.findall(r"\d+₽", money_letters))
        usd = to_int_or_zero(re.findall(r"\d+\$", money_letters))
        eur = to_int_or_zero(re.findall(r"\d+€", money_letters))

        address = re_space_finder.sub(" ", soup.find("div", text="Адрес").next_sibling.next_element.text.strip())
        worktime = re_space_finder.sub(" ", soup.find("div", text="Время работы").next_sibling.text.strip())

        return AtmInfo(rub=rub, usd=usd, eur=eur, address=address, worktime=worktime)

    except Exception as ex:
        print(datetime.datetime.now().isoformat(), "ERROR", coords, ex, sep=" | ")
    finally:
        driver.quit()

    return None
