import flet as ft
import requests

# エリア情報の取得
AREA_URL = "https://www.jma.go.jp/bosai/common/const/area.json"
area_data = requests.get(AREA_URL).json()

# 地方ごとの地域リストの作成
regions = {
    "北海道": ["016000"],
    "東北地方": ["020000", "030000", "040000", "050000", "060000", "070000"],
    "関東地方": ["080000", "090000", "100000", "110000", "120000", "130000", "140000"],
    "中部地方": ["150000", "160000", "170000", "180000", "190000", "200000", "210000", "220000", "230000"],
    "近畿地方": ["240000", "250000", "260000", "270000", "280000", "290000", "300000"],
    "中国地方": ["310000", "320000", "330000", "340000", "350000"],
    "四国地方": ["360000", "370000", "380000", "390000"],
    "九州地方": ["400000", "410000", "420000", "430000", "440000", "450000", "460100"],
    "沖縄地方": ["471000", "472000", "473000", "474000"]
}

# 地域名マッピング (code -> name)
area_name_mapping = {code: area['name'] for code, area in area_data['offices'].items()}

def fetch_weather_data(area_code):
    WEATHER_URL = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"
    print(f"Fetching data from: {WEATHER_URL}")
    response = requests.get(WEATHER_URL)
    response.raise_for_status()
    return response.json()

def main(page: ft.Page):
    weather_text = ft.Text("地域を選択してください。", expand=True)
    prefecture_dropdown = ft.Dropdown(expand=True)
    sub_area_dropdown = ft.Dropdown(expand=True)
    
    def update_prefecture_dropdown(region_name):
        prefecture_dropdown.options = [
            ft.dropdown.Option(code, text=area_name_mapping[code]) for code in regions[region_name]
        ]
        prefecture_dropdown.value = None
        sub_area_dropdown.options = []
        sub_area_dropdown.value = None
        weather_text.value = "地方を選択してください。"
        page.update()

    def update_sub_area_dropdown(area_code):
        sub_area_dropdown.options = []
        try:
            weather_data = fetch_weather_data(area_code)
            if weather_data and len(weather_data) > 0 and len(weather_data[0]['timeSeries']) > 0:
                time_series = weather_data[0]['timeSeries'][0]
                if 'areas' in time_series:
                    for area in time_series['areas']:
                        sub_area_dropdown.options.append(
                            ft.dropdown.Option(area['area']['code'], text=area['area']['name'])
                        )
        except Exception as ex:
            print(f"Error fetching data for code {area_code}: {ex}")
        sub_area_dropdown.value = None
        weather_text.value = "地域を選択してください。"
        page.update()

    def on_region_change(e):
        selected_index = e.control.selected_index
        region_name = list(regions.keys())[selected_index]
        update_prefecture_dropdown(region_name)

    def on_prefecture_change(e):
        area_code = prefecture_dropdown.value
        if area_code:
            update_sub_area_dropdown(area_code)
        else:
            sub_area_dropdown.options = []
            sub_area_dropdown.value = None
            weather_text.value = "地方を選択してください。"
        page.update()

    def on_sub_area_change(e):
        selected_code = sub_area_dropdown.value
        if selected_code:
            try:
                weather_info = fetch_weather_data(prefecture_dropdown.value)
                weather_text_content = ""
                if weather_info and len(weather_info) > 0 and len(weather_info[0]['timeSeries']) > 0:
                    time_series = weather_info[0]['timeSeries'][0]
                    selected_sub_area = next(
                        area for area in time_series['areas'] if area['area']['code'] == selected_code)
                    weather_text_content += f"地域: {selected_sub_area['area']['name']}\n"
                    for i in range(len(time_series['timeDefines'])):
                        time = time_series['timeDefines'][i]
                        weather = selected_sub_area['weathers'][i]
                        wind = selected_sub_area['winds'][i]
                        wave = selected_sub_area.get('waves', [None] * len(time_series['timeDefines']))[i]
                        weather_text_content += f"{time}: 天気 - {weather}, 風 - {wind}, 波 - {wave}\n"
                weather_text.value = weather_text_content if weather_text_content else "天気情報がありません。"
            except Exception as ex:
                weather_text.value = f"天気情報の取得に失敗しました: {ex}"
        else:
            weather_text.value = "地域を選択してください。"
        page.update()

    rail_destinations = [
        ft.NavigationRailDestination(
            icon=ft.icons.LOCATION_CITY,
            label=region
        )
        for region in regions.keys()
    ]
    
    navigation_rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        destinations=rail_destinations,
        on_change=on_region_change
    )

    # 初回実行時の設定
    initial_region_name = list(regions.keys())[0]
    update_prefecture_dropdown(initial_region_name)
    
    prefecture_dropdown.on_change = on_prefecture_change
    sub_area_dropdown.on_change = on_sub_area_change
    
    page.add(
        ft.Row(
            [
                navigation_rail,
                ft.VerticalDivider(width=1),
                ft.Column(
                    [
                        ft.Row([ft.Text("地方を選択: "), prefecture_dropdown]),
                        ft.Row([ft.Text("地域を選択: "), sub_area_dropdown]),
                        weather_text,
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    expand=True
                ),
            ],
            expand=True
        )
    )

ft.app(target=main)