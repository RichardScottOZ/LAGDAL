from langchain import LLMMathChain, SerpAPIWrapper
from langchain.agents import AgentType, Tool, initialize_agent, tool
from langchain.chat_models import ChatOpenAI
from langchain.schema import (
    AIMessage,
    HumanMessage,
    SystemMessage
)
from langchain.tools import BaseTool

from langchain.chains import LLMChain
from langchain.llms import OpenAI

from langchain.text_splitter import CharacterTextSplitter
from langchain.chains.mapreduce import MapReduceChain
from langchain.chains.summarize import load_summarize_chain
from langchain.docstore.document import Document

# import openai as openaiNotLC

from util import append_experiment_results

from prompts import promptCombineAndRewordInStyle, promptIsThisAbout, promptGeologicalRegions, promptLocationWithinRegions

from prompts import promptDecideIfCountySmall, promptCombineAndRewordInStyleB

### functions functions
from native_skills.macrostrat.macrostrat import getPointLocationStratColumn, macrostratOnlyReturnFirstTwoLayers, macrostratOnlyReturnFirstLayer, ifNoSurfaceGeology
#### macrostrat prompts
from native_skills.macrostrat.macrostrat import macroStratColSummarizationTop, macroStratColSummarizationSecondMostLayer, macroStratColSummarization, macroStratColSummarizationWhenNoColumn

from native_skills.bing.geocoding import getStateAndCountyFromLatLong, getAddressFromLatLong, getPointLocationFromCityStateAndCounty

from native_skills.wikipedia.wikipedia import getWikipediaPageAndProcess, extractContentFromWikipediaPageContent

# llm = ChatOpenAI(temperature=0)
# llm = OpenAI(model_name="text-davinci-003",temperature=0.2, max_tokens=256)
#llm = OpenAI(model_name="text-davinci-003",temperature=0.2) ### works mostly
# llm = OpenAI(model_name="text-davinci-003",temperature=0.2,max_tokens=4096) ### does not work as too short!
#llm = OpenAI(model_name="gpt-3.5-turbo",temperature=0.2) ### can only do chat? not text?
# llm = OpenAI(model_name="gpt-4",temperature=0.2, max_tokens=4096)
llm = OpenAI(model_name="text-davinci-003",temperature=0.2)

llm_math_chain = LLMMathChain(llm=llm, verbose=True)

# llm_4a = OpenAI(model_name="gpt-4",temperature=0.2, max_tokens=4096)

chat = ChatOpenAI(model_name="gpt-3.5-turbo",temperature=0)

def callChatGPT4(inputString:str):
    request = "What is the geologic story around "+inputString+" ? Break it down by time period and keep it under 12 sentences."
    print('chatGPT request is',request)
    messages = [
    SystemMessage(content="You are a helpful assistant that summarizes regional geology."),
    HumanMessage(content=request)
    ]
    completion = chat(messages)
    #completion = openaiNotLC.ChatCompletion.create( model="gpt-4", messages=[{"role": "user", "content": "What is the geologic story around  Estes Park, Colorado USA ? Break it down by time period and keep it under 12 sentences."} ] ) 
    print(completion)
    return completion

#### from main
# from main import macrostratGeologyForLocation

def getPointLocationFromCityStateAndCountyMod(inputString:str):
    city, state, country = inputString.split(",")
    response_object = getPointLocationFromCityStateAndCounty(city, state, country)
    return response_object

def getMacroStratAPIBasic(latLong:str):
    a, b = latLong.split(",")
    macrostrat_column_json  = getPointLocationStratColumn(float(a),float(b))
    #return macrostrat_column_json
    return macrostratGeologyForLocationMod(macrostrat_column_json)
                                

def macrostratGeologyForLocationMod(macrostrat_column_json):
    # macrostrat_column_json = getPointLocationStratColumn(latitude,longitude)
    if macrostrat_column_json == "No stratigraphic column data available for this location.":
        #print("No stratigraphic column data available for this location of: ",latitude,longitude, " so we will try to get surface geology data.")
        macrostrat_map_json = ifNoSurfaceGeology(latitude,longitude)
        #print("macrostrat_map_json map geologic data is",macrostrat_map_json)
        #### Using prompt for map data when there is no stratigraphic column data
        chainMacroStratWhenNotColum = LLMChain(llm=llm, prompt=macroStratColSummarizationWhenNoColumn)
        response = chainMacroStratWhenNotColum.run(macrostrat_map_json)
        
    else:
        #print("Found a stratigraphic column data available for this location of. ",latitude,longitude)
        macrostrat_column_json = macrostratOnlyReturnFirstTwoLayers(macrostrat_column_json)
        #### Using prompt for stratigraphic column data
        chainMacroStrat = LLMChain(llm=llm, prompt=macroStratColSummarization)
        response = chainMacroStrat.run(macrostrat_column_json)
    return response





def checkIfTextAbout(stringInput:str):
    subject, response = stringInput.split(",")
    objectInput = {"subject":subject,"text":response}
    checkIfTextAbout = LLMChain(llm=llm, prompt=promptIsThisAbout)
    print("The objectInput is",objectInput)
    print("The objectInput type is",type(objectInput))
    checkIfTextAbout = checkIfTextAbout.run(objectInput)
    return checkIfTextAbout


def regionalGeologyOfStateFromWikipedia(inputString:str):
    chainWiki = LLMChain(llm=llm, prompt=extractContentFromWikipediaPageContent)
    state, country, regional_geology_subarea = inputString.split(",")
    stateAndCountry = {"state":state,"country":country}
    #search_term = "Geology of "+stateAndCountry["state"]+" state, "+stateAndCountry["country"]
    search_term = "Geology of "+ stateAndCountry["country"]
    if("United States" in country or "USA" in country):
        search_term = "Geology of "+stateAndCountry["state"]
    else:
        search_term = "Geology of "+stateAndCountry["state"]+ country
    
    print("wikipedia search_term = ",search_term)
    wikipedia_page_object = getWikipediaPageAndProcess(search_term,stateAndCountry)
    page_content = wikipedia_page_object["content"]
    text_splitter = CharacterTextSplitter()
    texts = text_splitter.split_text(page_content)
    docs = [Document(page_content=t) for t in texts[:3]]
    chain = load_summarize_chain(llm, chain_type="map_reduce")
    summarized_wikipedia = chain.run(docs)
    wikipedia_page_title = wikipedia_page_object["title"]
    return {"wikipedia_page_title":wikipedia_page_title,"wikipedia_page_content":summarized_wikipedia,"subject_to_extract":regional_geology_subarea}
    # response = chainWiki.run({"subject_to_extract":regional_geology_subarea,"wikipedia_page_content":summarized_wikipedia})
    # if "No" in checkIfTextAbout.run({"subject":"geology","text":response}) or "No" in checkIfTextAbout.run({"subject":stateAndCountry["country"],"text":response}):
    #     ### deferring to direct prompt
    #     ### decide if we want to use the prompt for the state or the country
    #     sizeOfCountryInKilometers_chain = LLMChain(llm=llm, prompt=promptDecideIfCountySmall)
    #     sizeOfCountryInKilometers = sizeOfCountryInKilometers_chain.run(stateAndCountry["country"])
    #     if int(sizeOfCountryInKilometers) > 500000:
    #         geology_regions_chain = LLMChain(llm=llm, prompt=promptGeologicalRegions)
    #         response = geology_regions_chain.run(stateAndCountry["state"])
    #     else:
    #         response = geology_regions_chain.run(stateAndCountry["country"])
    #     return {"summary":response,"wikipedia_page_title":"regional geology areas prompt"}
        
    # else: 
    #     return {"summary":response,"wikipedia_page_title":wikipedia_page_title}

# You can also define an args_schema to provide more information about inputs
from pydantic import BaseModel, Field

class CalculatorInput(BaseModel):
    query: str = Field(description="should be a math expression")

        
tools = [
    Tool(
        name="Calculator",
        func=llm_math_chain.run,
        description="Useful for when you need to answer questions about math",
        # args_schema=CalculatorInput
    ),
]

tools.append(
    Tool(
        name="Check-if-text-about-subject",
        func=checkIfTextAbout,
        description="""
        Useful for determining if a text is about a particular subject.
        The input to this tool should be a comma separated list of strings.
        It should take the form of `"subject","text to check if about subject"`.
        """,
    )
)
tools.append(
    Tool(
        name="get-state-country-from-lat-long",
        func=getStateAndCountyFromLatLong,
        description="""
        Useful for finding the state and county for a given point location defined by latitude and longitude.
        The input to this tool should be a comma separated list of numbers of length two,representing latitude and longitude. 
        For example, `40.7128,-74.0060` would be the input for a location at latitude 40.7128 and longitude -74.0060
        """,
    )
)
tools.append(
    Tool(
        name="get-street-address-from-lat-long",
        func=getPointLocationFromCityStateAndCountyMod,
        description="""
        Useful for finding the street address for a given point location defined by latitude and longitude.
        The input to this tool should be a comma separated list of strings representing city, state, and country. 
        For example, "Houston, Texas, USA""
        """
    )
)
# tools.append(
#     Tool(
#         name="find-regional-geology-of-state-using-wikipedia",
#         func=regionalGeologyOfStateFromWikipedia,
#         description="""
#         Useful for finding the regional geology of a geographic area using wikipedia.
#         The input to this tool should be a comma separated list of strings 
#         It should contain state, country, and the string 'regional geologic history'. 
#         For example, `"Texas", "United States of America", "regional geologic history"`.
#         """
#     )
# )
tools.append(
    Tool(
        name="Macrostrat-Geology-For-Location",
        func=getMacroStratAPIBasic,
        description="""
        Useful for finding a description the top two layers of the stratigraphic column for a given point location.
        The input to this tool should be a comma separated list of numbers of length two,representing latitude and longitude. 
        For example, `40.7128,-74.0060` would be the input for a location at latitude 40.7128 and longitude -74.0060
        """,
    ),
)
tools.append(
    Tool(
        name="get-point-location-from-city-state-and-country",
        func=getPointLocationFromCityStateAndCountyMod,
        description="""
        Useful for finding the latitude and longitude for a given point location defined by city, state, and country.
        The input to this tool should be a comma separated list of strings 
        It should contain city, state, and country'. 
        For example, `"Houston, Texas, United States of America"`.
        """
    )
)
tools.append(
    Tool(
        name="get-regional-geology-from-chatGPT4",
        func=callChatGPT4,
        description="""
        Useful for finding the regional geology of an area. Better than wikipedia.
        The input to this tool should be a single string describing the location. It can be a city, state, and country or a latitude and longitude if not near a city.
        For example, `"Houston, Texas, United States of America"` or `Oslo, Norway` or if not near a city than a latitude and longitude such as `40.7128,-74.0060` of `51.36° N, 91.62° W`.
        """
    )
)


agent = initialize_agent(tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True)

# agent.run("""
#           Get the latitude and longitude of Port Clinton, Ohio and 
#           tell me the geology of that location, 
#           if there is any age gap between the top two layers, 
#           and how that local geology fits into regional geologic story.
#           Do so as if you are talking to students on a geology field trip looking at an outcrop.
#           """)

# agent.run("""
#           Get the latitude and longitude of Port Clinton, Ohio.
#           Is there any volcanic rocks there?
#           """)

# agent.run("""
#           Get the latitude and longitude of Houston, Texas.
#           Is there any sedimentary rocks there?
#           """)

### This one does not work out well!
# agent.run("""
#           Get the latitude and longitude of Olso, Norway and the local geology.
#           Determine the age of any rocks there that are metamorphic.
#           """)

# agent.run("""
#           Get the latitude and longitude of Estes Park, Colorado, United States and 
#           tell me the geology of that location, 
#           and how the local geology fits into regional geologic story of Colarado.
#           """)

# agent.run("""
#           Tell me the geology Estes Park, Colorado, United States
#           and how the local geology fits into regional geologic story
#           """)

# agent.run("""
#           Tell me how the surface geology of Estes Park, Colorado, United States
#           fits into recent regional geologic history of the area.
#           """)

# agent.run("""
#           Tell me how the surface geology of Port Clinton, Ohio, United States
#           fits into geologic history of the area. Do so in a way that is understandable to students on a geology field trip.
#           Tell me at least 15 to 30 sentences.
#           """)

agent.run("""
          Tell me the geology of Port Clinton, Ohio, USA
          Be sure to explain how the local geology fits into regional geologic narrative.
          Say at least 10 to 20 sentences.
          """)
## Try to add memory: https://python.langchain.com/en/latest/modules/memory/examples/agent_with_memory.html