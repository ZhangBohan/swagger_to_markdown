import requests
import os

import sys


class SwaggerData(object):

    def __init__(self, doc_url, user='', password=''):
        self.url = doc_url
        self.user = user
        self.password = password

    def _get_api_docs(self):
        r = requests.get(self.url)
        result = r.json()
        return result['paths']

    def get_api_category_urls(self):
        """
        获取api所有分类的url

        """
        apis = self._get_api_docs()
        request_urls = []
        for api in apis:
            request_url = os.path.join(self.url, api['path'][1:])
            request_urls.append(request_url)
        return request_urls

    def get_category_detail(self, category_url):
        """
        获取每一个api分类下的所有api信息
        :param api_url:
        :return:
        """
        r = requests.get(category_url, auth=(self.user, self.password))
        detail_json = r.json()
        serializer_models = detail_json.get('models')
        if not serializer_models:
            return []

        category_info = []
        for item in detail_json['apis']:
            for operation in item['operations']:
                path = item['path']
                method = operation['method']
                summary = operation['summary']
                operation_type = operation['type']

                parameters = [] or operation['parameters']
                query_info_item = {'path': path,
                                   'method': method,
                                   'summary': summary,
                                   'parameters': parameters}

                if operation_type in serializer_models:
                    serializer_model = operation_type

                if operation_type == 'array':
                    serializer_model = operation['items']['$ref']

                if operation_type == 'object':
                    continue

                response_info_item = serializer_models[serializer_model]['properties']

                if 'results' in response_info_item:
                    internal_serializer = response_info_item['results']['items']['$ref']
                    internal_res = serializer_models[internal_serializer]['properties']
                    response_info_item['results'].update(items=internal_res)

                category_info.append({'query_info': query_info_item, 'res_info': response_info_item})

        return category_info

    def res_info(self, data):
        res_info = "{\n"
        for k, v in data.items():
            if k == 'items':
                res_info += "    items: [\n        {\n"
                for internal_k, internal_v in sorted(v['properties'].items()):
                    res_info += "        {0} {1} {2}\n".\
                        format(internal_k,
                               internal_v['type'],
                               internal_v['description'] if 'description' in internal_v and
                                                            internal_v['description'] else '')
                res_info += "        }\n    ]\n"
                continue
            elif v == 'object':
                for internal_k, internal_v in sorted(data['properties'].items()):
                    res_info += "    {0} {1} {2}\n". \
                        format(internal_k,
                               internal_v['type'],
                               internal_v['description'] if 'description' in internal_v and
                                                            internal_v['description'] else '')
        res_info += "}"
        return res_info

    def params_info(self, data):
        param_info_first = "| 参数名 | 类型 | 描述 | 是否必填 | 参数类型 \n| ---- | ---- |  ---- |  ---- | ---- \n"
        param_info_second = "| 参数名 | 类型 | 描述 | 是否必填 | 参数类型 \n| ---- | ---- |  ---- |  ---- | ---- \n"
        params = data['parameters']
        for item in params:
            if item['in'] == 'body':
                for key, property in item['schema']['properties'].items():
                    param_info_second += "| {0} | `{1}` | {2} | {3} | {4}\n". \
                        format(key,
                               property['type'],
                               property['description'] if 'description' in property else '',
                               'true' if key in item['schema'].get('required', []) else '',
                               'body')
            else:
                param_info_first += "| {0} | `{1}` | {2} | {3} | {4}\n". \
                    format(item['name'],
                           item['type'],
                           item['description'] if 'description' in item else '',
                           item['required'],
                           item['in'])
        if param_info_first == "| 参数名 | 类型 | 描述 | 是否必填 | 参数类型 \n| ---- | ---- |  ---- |  ---- | ---- \n":
            param_info_first = ""

        if param_info_second == "| 参数名 | 类型 | 描述 | 是否必填 | 参数类型 \n| ---- | ---- |  ---- |  ---- | ---- \n":
            param_info_second = ""

        if param_info_first == param_info_second == "":
            return "| 参数名 | 类型 | 描述 | 是否必填 | 参数类型 \n| ---- | ---- |  ---- |  ---- | ---- \n"
        else:
            return param_info_first + "\n" + param_info_second

    def format_markdown(self, path, title, method, data):

        # print(data)
        responses = data['responses']
        result = responses.get('200') or responses.get('201') or responses.get('204')
        res_info = self.res_info(result['schema'])
        params_info = self.params_info(data)

        mk_str = "#{0}\n\n- URL: `{1}`\n- METHOD: `{2}`\n\n请求参数\n" \
                 "\n{3}\n返回结果\n\n```\n{4}\n```".format(title, path, method, params_info, res_info)
        return mk_str


def main(doc_url):
    s = SwaggerData(doc_url)
    apis = s._get_api_docs()

    main_content = ""
    for prefix, method_data in apis.items():
        for method, data in method_data.items():
            path = prefix
            title = data.get('summary', path + method)
            content = s.format_markdown(path=path, title=title, method=method, data=data)

            href = '{0}{1}'.format(path, method)
            main_content += '* [{0}]({1})`{2}` `{3}`\r\n'.format(title, href, method.upper(), href)

            # print('slug: %s' % path)
            # print('title: %s' % title)
            # print('content: %s' % content)
            os.makedirs('.{0}'.format(path), exist_ok=True)
            file = '.{0}{1}.md'.format(path, method)

            with open(file, 'w', encoding='utf8') as f:
                f.write(content)

    with open('api/API.md', 'w', encoding='utf8') as f:
        f.write(main_content)

    print("success!")


if __name__ == '__main__':
    main(sys.argv[1])

