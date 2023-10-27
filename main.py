import requests
from urllib.parse import urlencode
from pprint import pprint
from datetime import datetime
import json
import os
from tqdm import tqdm

# Получение токена доступа ВК
app_id = '51778613'
oauth_base_url = 'https://oauth.vk.com/authorize'
params_for_token_getting = {
    'client_id': app_id,
    'redirect_uri': 'https://oauth.vk.com/blank.html',
    'page': 'page',
    'scope': 'photos',
    'response_type': 'token'
}

oauth_url = f'{oauth_base_url}?{urlencode(params_for_token_getting)}'
pprint(oauth_url)
print('Перейдите по ссылке выше, авторизуйтесь и скопируйте access_token из ссылки в браузере')

token = input('Введите access_token: ')
my_id = input('Введите id страницы ВК: ')
YD_token = input('Введите токен Яндекса: ')
vk_version = '5.131'


# Реализация класса по взаимодействию с фото в ВК
class ApiVk:
    api_base_url = 'https://api.vk.com/method'

    # Создание инициализации для экземпляров класса
    def __init__(self, access_token, user_id, version):
        self.access_token = access_token
        self.user_id = user_id
        self.version = version

    # Создание общих параметров, которые будут применяться во всех дополнительно вызываемых методах, если таковые понадобятся
    def _create_common_params(self):
        return {
            'access_token': self.access_token,
            'owner_id': self.user_id,
            'v': self.version
        }

    # Создание метода, получающего фотографии в максимальном размере и скачивающего их в проект
    def get_profile_max_size_photos(self):
        params = self._create_common_params()   # Получение общих параметров
        params.update({
            'album_id': 'profile',
            'extended': 1
        })  # Обновление параметров необходимыми для последующего запроса элементами
        response = requests.get(f'{self.api_base_url}/photos.get', params=params)
        # pprint(response.json())  # На случай необходимости посмотреть, как выглядит ответ ВК

        all_data = response.json()
        max_sizes_photos = {}  # Создание словаря, в который циклом ниже будет добавляться информация в формате {ссылка на фотографию: [число лайков, дата загрузки, тип максимального размера]}
        for el in tqdm(all_data['response']['items']):
            for el_ in tqdm(el['sizes']):
                if el_['type'] == 'z':  # Используется type 'z', т.к. type 'w', который согласно документации является максимальным по размеру, доступен, однако, не для всех фото
                    max_sizes_photos[el_['url']] = [el['likes']['count'], el['date'], el_['type']]

        # Код ниже преобразует unix-время, возвращаемое ВК, в привычный нам формат даты. ВАЖНОЕ УТОЧНЕНИЕ: такое преобразование в теории может вызвать потенциальные
        # проблемы в дальнейшее выполнение кода, т.к. есть вероятность возникновения ситуации, при которой фото загружались в один и тот же день и получили одинаковое число
        # лайков. Тогда следуя условию задания (если число лайков одинаково, добавить к названию дату), можем получить одинаковые названия для файлов и потерять часть
        # фото при их скачивании режимом 'w' в цикле. Однако принимаем данную ситуацию как маловероятную и используем преобразование даты
        for value in tqdm(max_sizes_photos.values()):
            value[1] = datetime.utcfromtimestamp(value[1]).strftime('%d-%m-%Y')

        # В задаче есть уточнение, что если кол-во лайков к фото совпадает, тогда к названию необходимо добавить дату фото. Ниже код, который реализует это требование
        count_of_likes = []  # Создание списка, куда циклом будем добавлять число лайков к каждому фото
        for value in tqdm(max_sizes_photos.values()):
            count_of_likes.append(value[0])
        # Добавление к числу лайков даты, если кол-во лайков к каким-то фото повторяется
        for value in tqdm(max_sizes_photos.values()):
            if value[0] in count_of_likes and count_of_likes.count(value[0]) > 1:
                value[0] = str(value[0]) + '_' + str(value[1])
        for value in tqdm(max_sizes_photos.values()):  # Преобразовываем кол-во лайков, которое будет названием фото, в строчный формат
            if isinstance(value[0], int):
                value[0] = str(value[0])
        # print(max_sizes_photos)  # На случай необходимости посмотреть, как выглядит полученный словарь

        # Наконец скачиваем (записываем) фото в папку проекта, используя ключи полученного ранее словаря как пути, а значения (первые эл-ты списка) как названия файлов
        for path, data in tqdm(max_sizes_photos.items()):
            response = requests.get(path)
            with open(f'{data[0]}.jpg', 'wb') as file:
                file.write(response.content)
        return max_sizes_photos


# Реализация класса по взаимодействию с фото на ЯД:
class ApiYd:
    api_base_url = 'https://cloud-api.yandex.net'

    # Создание инициализации для экземпляров класса
    def __init__(self, polygon_token):
        self.polygon_token = polygon_token
        self.method = ApiVk(token, my_id, vk_version)  # Создание метода, который позволит вызвать из описываемого класса (ApiYd) метод другого класса (ApiVk)

    # Создание общих параметров, которые будут применяться во всех дополнительно вызываемых методах, если таковые понадобятся
    def _create_common_params(self):
        return {
            'Authorization': f'OAuth {self.polygon_token}'
        }

    # Создание новой папки для загрузки фото
    def create_new_folder(self):
        folder_name = 'Курсовая_работа_Садака_Амир_pd86'
        headers = self._create_common_params()  # Вызываем заголовки авторизации
        params = {
            'path': folder_name
        }
        # Создание папки
        response = requests.put(f'{self.api_base_url}/v1/disk/resources', headers=headers, params=params)
        return folder_name  # Возвращаем название папки, т.к. оно понадобится в следующем методе

    # Создание метода, загружающего фото в созданную папку на диск и создающего json-файл с информацией по загруженным фото
    def photo_upload(self):
        headers = self._create_common_params()  # Вызываем заголовки авторизации

        # Создаем список, куда циклом будем помещать названия фотографий из полученного в классе VKApi словаря
        list_of_names = []
        for value in tqdm(self.method.get_profile_max_size_photos().values()):  # Вызываем метод, описанный в другом классе, который возвращает словарь
            list_of_names.append(f'{value[0]}.jpg')
        # print(list_of_names)  # На случай необходимости посмотреть, как выглядит полученный список

        # Создаем список параметров, необходимых для отправки запроса на получение путей загрузки
        list_of_params = []
        for el in tqdm(list_of_names):
            list_of_params.append({'path': f'{self.create_new_folder()}/{el}', 'overwrite': 'True'})
        # print(list_of_params)  # На случай необходимости посмотреть, как выглядит полученный список

        # Создаем словарь, в который в кач-ве ключа будем помещать пути для загрузки, полученные requests-запросом, а в кач-ве значения - название, которое нужно присвоить фотографии на ЯД
        list_of_paths = {}
        for params in tqdm(list_of_params):
            response = requests.get(f'{self.api_base_url}/v1/disk/resources/upload', params=params, headers=headers)
            list_of_paths[response.json()['href']] = params['path'].replace(f'{self.create_new_folder()}/', '')
        # print(list_of_paths) # На случай необходимости посмотреть, как выглядит полученный словарь

        # Наконец загружаем фото на ЯД и создаем необходимый json-файл
        count_of_uploaded_photo = int(input('Введите количество фотографий, которое нужно сохранить на ЯД: '))
        n = 0  # Счетчик загруженных фото
        data_for_json = []  # Сюда будем записывать информацию по загруженным фото
        for path, photo_name in tqdm(list_of_paths.items()):
            params = {
                'overwrite': 'True'
            }
            with open(photo_name, 'rb') as photo_for_upload:
                response = requests.put(path, params=params, data=photo_for_upload)
            data_for_json.append({'file_name': photo_name, 'size': 'z'})  # Уточнение: значение ключа size "захардкожено", т.к. мы изначально скачиваем фотографии только в том случае, если размер равен 'z'
            # В теории можно было бы создать условие, которое скачивает фотографию, соответствующую максимальному размеру height, однако, насколько я понял документацию, type 'z' возвращается всегда
            # в отличие от того же типа 'w'
            n += 1
            if n == count_of_uploaded_photo:  # Прерываем цикл, если кол-во загруженных фото достигло необходимого нам значения
                break
        # print(data_for_json) # На случай необходимости посмотреть, как выглядит полученный список со словарями
        current_path = os.getcwd()
        path_for_json = os.path.join(current_path, 'photo_info.json')
        with open(path_for_json, 'w', encoding='utf-8') as f:
            json.dump(data_for_json, f, ensure_ascii=False, indent=2)


vk_client = ApiVk(token, my_id, vk_version)
vk_client.get_profile_max_size_photos()
yd_client = ApiYd(YD_token)
yd_client.create_new_folder()
yd_client.photo_upload()
