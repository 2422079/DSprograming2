import sqlite3
import requests
from datetime import datetime
import flet as ft
import os

# データベースファイルが存在する場合、削除する
if os.path.exists('weather.db'):
    os.remove('weather.db')

AREA_URL = "https://www.jma.go.jp/bosai/common/const/area.json"
area_data = requests.get(AREA_URL).json()

valid_area_codes = [
    "011000", "012000", "013000", "014030", "014100", "015000", "016000", "017000",
    "020000", "030000", "040000", "050000", "060000", "070000", "080000", "090000",
    "100000", "110000", "120000", "130000", "140000", "150000", "160000", "170000",
    "180000", "190000", "200000", "210000", "220000", "230000", "240000", "250000",
    "260000", "270000", "280000", "290000", "300000", "310000", "320000", "330000",
    "340000", "350000", "360000", "370000", "380000", "390000", "400000", "410000",
    "420000", "430000", "440000", "450000", "460040", "460100", "471000", "472000",
    "473000", "474000"
]

regions_data = [
    ("北海道", ["011000", "012000", "013000", "014030", "014100", "015000", "016000", "017000"]),
    ("東北地方", ["020000", "030000", "040000", "050000", "060000", "070000"]),
    ("関東地方", ["080000", "090000", "100000", "110000", "120000", "130000", "140000"]),
    ("中部地方", ["150000", "160000", "170000", "180000", "190000", "200000", "210000", "220000", "230000"]),
    ("近畿地方", ["240000", "250000", "260000", "270000", "280000", "290000", "300000"]),
    ("中国地方", ["310000", "320000", "330000", "340000", "350000"]),
    ("四国地方", ["360000", "370000", "380000", "390000"]),
    ("九州地方", ["400000", "410000", "420000", "430000", "440000", "450000", "460100", "460040"]),
    ("沖縄地方", ["471000", "472000", "473000", "474000"]),
]

def setup_database():
    conn = sqlite3.connect('weather.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS region (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prefecture (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            region_id INTEGER,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            FOREIGN KEY (region_id) REFERENCES region (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS area (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prefecture_id INTEGER,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            FOREIGN KEY (prefecture_id) REFERENCES prefecture (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weather (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            area_id INTEGER,
            code TEXT NOT NULL,
            area_name TEXT,
            weather_description TEXT,
            wind TEXT,
            wave TEXT,
            FOREIGN KEY (area_id) REFERENCES area (id)
        )
    ''')
    conn.commit()
    conn.close()

def insert_data():
    conn = sqlite3.connect('weather.db')
    cursor = conn.cursor()
    area_name_mapping = {code: area['name'] for code, area in area_data['offices'].items()}

    def insert_region(region_code, region_name):
        cursor.execute('SELECT id FROM region WHERE code = ?', (region_code,))
        region_id = cursor.fetchone()
        if not region_id:
            cursor.execute('INSERT INTO region (code, name) VALUES (?, ?)', (region_code, region_name))
            region_id = cursor.lastrowid
        else:
            region_id = region_id[0]
        return region_id

    def insert_prefecture(region_id, prefecture_code, prefecture_name):
        cursor.execute('SELECT id FROM prefecture WHERE code = ?', (prefecture_code,))
        prefecture_id = cursor.fetchone()
        if not prefecture_id:
            cursor.execute('INSERT INTO prefecture (region_id, code, name) VALUES (?, ?, ?)', (region_id, prefecture_code, prefecture_name))
            prefecture_id = cursor.lastrowid
        else:
            prefecture_id = prefecture_id[0]
        return prefecture_id

    def insert_area(prefecture_id, area_code, area_name):
        cursor.execute('SELECT id FROM area WHERE code = ?', (area_code,))
        if not cursor.fetchone():
            cursor.execute('INSERT INTO area (prefecture_id, code, name) VALUES (?, ?, ?)', (prefecture_id, area_code, area_name))

    for region_name, prefecture_codes in regions_data:
        region_code = prefecture_codes[0][:2]  # 都道府県コードから地域コードを取得
        region_id = insert_region(region_code, region_name)

        for code in prefecture_codes:
            if code in area_name_mapping:
                prefecture_name = area_name_mapping[code]
                prefecture_id = insert_prefecture(region_id, code, prefecture_name)

                if 'class15s' in area_data:
                    for area_code, class_info in area_data['class15s'].items():
                        if class_info['parent'] == code:
                            area_name = class_info['name']
                            insert_area(prefecture_id, area_code, area_name)
                if 'class10s' in area_data:
                    for area_code, class_info in area_data['class10s'].items():
                        if class_info['parent'] == code:
                            area_name = class_info['name']
                            insert_area(prefecture_id, area_code, area_name)
                if 'class20s' in area_data:
                    for area_code, class_info in area_data['class20s'].items():
                        if class_info['parent'] == code:
                            area_name = class_info['name']
                            insert_area(prefecture_id, area_code, area_name)
    conn.commit()
    conn.close()

def fetch_weather_data(area_code):
    if area_code not in valid_area_codes:
        print(f"地域コード {area_code} は無効です。")
        return None
    WEATHER_URL = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"
    try:
        response = requests.get(WEATHER_URL)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as err:
        print(f"HTTP error occurred: {err}")
        if err.response.status_code == 404:
            print(f"地域コード {area_code} のデータは存在しません。")
    except requests.exceptions.RequestException as err:
        print(f"Error occurred: {err}")
    return None

def insert_weather_data(weather_data, area_code):
    if weather_data:
        try:
            conn = sqlite3.connect('weather.db')
            for forecast in weather_data:
                if 'timeSeries' not in forecast:
                    continue
                time_series_list = forecast['timeSeries']
                if not time_series_list:
                    continue

                time_series = time_series_list[0]
                if 'areas' not in time_series:
                    continue

                for area in time_series['areas']:
                    area_code = area['area']['code']
                    cursor = conn.cursor()
                    cursor.execute('SELECT id FROM area WHERE code = ?', (area_code,))
                    area_id = cursor.fetchone()
                    if not area_id:
                        continue
                    area_id = area_id[0]

                    for i in range(min(3, len(time_series['timeDefines']))):  # 3日分のデータのみ取得
                        date = time_series['timeDefines'][i]
                        area_name = area['area']['name']
                        weather_description = area.get('weathers', ["なし"]*3)[i]
                        wind = area.get('winds', ["なし"]*3)[i]
                        wave = area.get('waves', ["なし"]*3)[i]
                        insert_weather(conn, date, area_id, area_code, area_name, weather_description, wind, wave)
            conn.close()
        except Exception as ex:
            print(f"天気データのデータベースへの挿入に失敗しました: {ex}")

def insert_weather(conn, date, area_id, code, area_name, weather_description, wind, wave):
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM weather WHERE date = ? AND area_id = ? AND code = ?', (date, area_id, code))
    if not cursor.fetchone():
        cursor.execute('INSERT INTO weather (date, area_id, code, area_name, weather_description, wind, wave) VALUES (?, ?, ?, ?, ?, ?, ?)', (date, area_id, code, area_name, weather_description, wind, wave))
        conn.commit()

def fetch_all_weather_data():
    for area_code in valid_area_codes:
        weather_data = fetch_weather_data(area_code)
        insert_weather_data(weather_data, area_code)

def get_regions():
    conn = sqlite3.connect('weather.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM region')
    regions = cursor.fetchall()
    conn.close()
    return regions

def get_prefectures(region_id):
    conn = sqlite3.connect('weather.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, code FROM prefecture WHERE region_id = ?', (region_id,))
    prefectures = cursor.fetchall()
    conn.close()
    return prefectures

def get_areas(prefecture_id):
    conn = sqlite3.connect('weather.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, code FROM area WHERE prefecture_id = ?', (prefecture_id,))
    areas = cursor.fetchall()
    conn.close()
    return areas

def get_weather_data(area_id):
    conn = sqlite3.connect('weather.db')
    cursor = conn.cursor()
    cursor.execute('SELECT date, weather_description, wind, wave FROM weather WHERE area_id = ?', (area_id,))
    weather_data = cursor.fetchall()
    conn.close()
    return weather_data

def main(page: ft.Page):
    setup_database()
    insert_data()
    fetch_all_weather_data()
    weather_text = ft.Text("地域を選択してください。", expand=True)
    prefecture_dropdown = ft.Dropdown(expand=True)
    sub_area_dropdown = ft.Dropdown(expand=True)

    def update_prefecture_dropdown(region_id):
        prefectures = get_prefectures(region_id)
        prefecture_dropdown.options = [
            ft.dropdown.Option(pref_id, text=name) for pref_id, name, code in prefectures
        ]
        prefecture_dropdown.value = None
        sub_area_dropdown.options = []
        sub_area_dropdown.value = None
        weather_text.value = "都道府県を選択してください。"
        page.update()

    def update_sub_area_dropdown(prefecture_id):
        areas = get_areas(prefecture_id)
        sub_area_dropdown.options = [
            ft.dropdown.Option(area_id, text=name) for area_id, name, code in areas
        ]
        sub_area_dropdown.value = None
        weather_text.value = "地域を選択してください。"
        page.update()

    def fetch_and_display_weather(area_id):
        weather_data = get_weather_data(area_id)
        if weather_data:
            weather_text_content = ""
            for date, weather_description, wind, wave in weather_data:
                weather_text_content += f"{date}: 天気 - {weather_description}, 風 - {wind}, 波 - {wave}\n"
            weather_text.value = weather_text_content if weather_text_content else "天気情報がありません。"
        else:
            weather_text.value = "天気情報がありません。"
        page.update()

    def on_region_change(e):
        selected_index = e.control.selected_index
        region_id = regions[selected_index][0]
        update_prefecture_dropdown(region_id)

    def on_prefecture_change(e):
        prefecture_id = prefecture_dropdown.value
        if prefecture_id:
            update_sub_area_dropdown(prefecture_id)
        else:
            sub_area_dropdown.options = []
            sub_area_dropdown.value = None
            weather_text.value = "都道府県を選択してください。"
        page.update()

    def on_sub_area_change(e):
        selected_area_id = sub_area_dropdown.value
        if selected_area_id:
            fetch_and_display_weather(selected_area_id)
        else:
            weather_text.value = "地域を選択してください。"
        page.update()

    regions = get_regions()
    rail_destinations = [
        ft.NavigationRailDestination(
            icon=ft.icons.LOCATION_CITY,
            label=region_name
        )
        for region_id, region_name in regions
    ]
    navigation_rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        destinations=rail_destinations,
        on_change=on_region_change
    )

    initial_region_id = regions[0][0]
    update_prefecture_dropdown(initial_region_id)
    prefecture_dropdown.on_change = on_prefecture_change
    sub_area_dropdown.on_change = on_sub_area_change

    page.add(
        ft.Row(
            [
                navigation_rail,
                ft.VerticalDivider(width=1),
                ft.Column(
                    [
                        ft.Row([ft.Text("都道府県を選択: "), prefecture_dropdown]),
                        ft.Row([ft.Text("地域を選択: "), sub_area_dropdown]),
                        weather_text,
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    expand=True
                )
            ],
            expand=True
        )
    )

ft.app(target=main)