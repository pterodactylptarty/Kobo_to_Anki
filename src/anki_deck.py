import genanki


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
  1702925616,
  'Python Test Model',
  fields=[
    {'name': 'German'},
    {'name': 'English'},
    {'name': 'MyMedia'}
  ],
  templates=[
    {
      'name': 'Card 1',
      'qfmt': '{{German}}<br>{{MyMedia}}',
      'afmt': '{{FrontSide}}<hr id="answer"><div class="english-sentence">{{English}}</div>',
    },
  ],
    css=my_css

)


#TODO: make deck unique to the filtered annotations.

# my_deck = genanki.Deck(
#   1565894783,
#   'German translations')
#

