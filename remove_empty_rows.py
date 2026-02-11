import csv

with open('data.csv', mode='r') as infile, \
     open('cleaned_data.csv', mode='w', newline='') as outfile:

    reader = csv.reader(infile)
    writer = csv.writer(outfile)

    for index, row in enumerate(reader):
        if index == 0 or index % 2 == 1:
            writer.writerow(row)