import csv
import deepl


###TODO: figure out how to incorporate with other functions.

#DeepL: 39b72c5b-fd7a-4202-81e0-97503e999e6b:fx

auth_key = "39b72c5b-fd7a-4202-81e0-97503e999e6b:fx"  # Replace with your key
translator = deepl.Translator(auth_key)

result = translator.translate_text("Hello, world!", target_lang="FR")
print(result.text)  # "Bonjour, le monde !"

with open('../winter_annotations.csv', newline='') as csvfile:
    csvreader = csv.reader(csvfile, delimiter=',')
    next(csvreader, None)  # Skip the header row if there is one
    for row in csvreader:
        print(row[0])
        # # Access and process the specific column here
        # specific_column_value = row[column_index]
        # print(specific_column_value)


def to_eng_csv(csv_path, csv_output):
    with open(csv_path, newline='') as csvfile, open(csv_output, 'w', newline='') as outfile:
        csvreader = csv.reader(csvfile, delimiter=',')
        csvwriter = csv.writer(outfile, delimiter=',')

        csvwriter.writerow(['Original', 'Translated'])

        next(csvreader, None)  # Skip the header row if there is one

        for row in csvreader:
            translation = translator.translate_text(row[0], target_lang="EN-US")
            paired_translation = (row[0], translation)
            csvwriter.writerow(paired_translation)


to_eng_csv('../winter_annotations.csv', "test_output.csv")
    #
    # results = fetch_annotations(author, title, start_date, end_date)
    # with open(file_name, mode='w', newline='', encoding='utf-8') as file:
    #     writer = csv.writer(file)
    #     writer.writerow(['Text', 'Annotation', 'DateCreated', 'Author', 'BookTitle'])
    #     print(results[:5])
    #     writer.writerows(results)
