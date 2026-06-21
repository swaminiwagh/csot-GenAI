import os, json
from dotenv import load_dotenv
from openai import OpenAI
load_dotenv()
client = OpenAI(base_url='https://openrouter.ai/api/v1', api_key=os.environ['OPENROUTER_API_KEY'])

TOOLS_SCHEMA = [{'type':'function','function':{'name':'web_search','description':'Search the web','parameters':{'type':'object','properties':{'query':{'type':'string'}},'required':['query']}}}]

messages = [
    {'role':'user','content':'what is LightRAG'},
    {'role':'assistant','content':'','tool_calls':[{'id':'abc123','type':'function','function':{'name':'web_search','arguments':'{"query":"LightRAG"}'}}]},
    {'role':'tool','tool_call_id':'abc123','content':'{"results":[{"title":"LightRAG GitHub","link":"https://github.com/hkuds/lightrag","snippet":"LightRAG is a lightweight RAG framework"}]}'}
]

response = client.chat.completions.create(model='deepseek/deepseek-chat', messages=messages, tools=TOOLS_SCHEMA, tool_choice='auto')
msg = response.choices[0].message
print('ROUND 2 CONTENT:', repr(msg.content))
print('ROUND 2 TOOL CALLS:', msg.tool_calls)
print('FINISH REASON:', response.choices[0].finish_reason)