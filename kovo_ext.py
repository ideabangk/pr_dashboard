import re
from playwright.sync_api import Playwright, sync_playwright, expect
import pandas as pd
from io import StringIO
import time
# 팀기록, 선수기록
# 남자부, 여자부
#types = ['오픈공격', '시간차공격','이동공격','후위공격','속공','퀵오픈']
types = ['속공','퀵오픈']
genders =['남자부','여자부']
# 
def kovo_ext(playwright: Playwright, type) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://kovo.co.kr/")
    page.goto("https://kovo.co.kr/KOVO")
    page.get_by_role("button", name="STATS").click()
    page.get_by_role("tab", name="선수 기록").click()
    #time.sleep(5)
    page.locator(".ant-select-selector").first.click()
    page.get_by_text("도드람 2024-2025 V-리그").click()
    page.locator("div").filter(has_text=re.compile(r"^진에어 2025-2026 V-리그$")).nth(2).click()
    page.get_by_text("도드람 2024-2025 V-리그").nth(2).click()
    page.locator("div").filter(has_text=re.compile(r"^1 Round$")).nth(3).click()
    page.get_by_text("6 Round").click()
    page.locator(".hidden > .ant-select > .ant-select-selector").first.click()
    page.get_by_title(type).locator("div").click()
    page.get_by_role("button", name="기록 보기").click()
    time.sleep(1)
    # 테이블 파싱 - locator: selector copy
    tables = page.locator("#root > article > div > article > section > article > div > section.css-1g6h5ls > table").evaluate("element => element.outerHTML")
    #tables = page.locator("#root > article > div > article > section > article > div > section.css-1g6h5ls > table").evaluate("element => element.outerHTML")
    df = pd.read_html(StringIO(tables), header=0)[0]
    #print(df)
    df.to_csv(f'data/kovo_men_{type}.csv',index=False, encoding='utf-8')
    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    for type in types:
        kovo_ext(playwright, type)
