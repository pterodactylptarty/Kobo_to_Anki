import genanki
## DeepL api auth key
auth_key = "39b72c5b-fd7a-4202-81e0-97503e999e6b:fx"  # Replace with your key




my_css = """
.card {
font-family: arial;
font-size: 20px;
text-align: center;
color: black;
background-color: white;
}


.english-sentence {
font-size: 19px;
font-style: italic;
}

"""

my_model = genanki.Model(
  1702925615000,
  'Python Test Model',
  fields=[
    {'name': 'Language'},
    {'name': 'English'},
    {'name': 'MyMedia'}
  ],
  templates=[
    {
      'name': 'Card 1',
      'qfmt': '{{Language}}<br>{{MyMedia}}',
      'afmt': '{{FrontSide}}<hr id="answer"><div class="english-sentence">{{English}}</div>',
    },
  ],
    css=my_css

)


#Voice for language:
speaker = "Anna" ## default german.

## TODO: think about whether to add language parameter in funcitons part. Then language selected can maybe map to a voice defined here.