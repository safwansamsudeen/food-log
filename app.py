from datetime import datetime
import pandas as pd
import io


import food_log_functions as flf

DATA_PATH = 'Food Log Data App.xlsx'
BANNED_ITEMS = ['Fasting']
food_log = flf.get_food_log(DATA_PATH)
# Replace fastings with blank

mapping, side_dishes = flf.get_updated_mapping(
    food_log, DATA_PATH, mapping_index_col='entered_name', food_item_col='food_item', banned_items=BANNED_ITEMS)
food_log = flf.cleanup_food_log(food_log, mapping, BANNED_ITEMS)

food_data = flf.get_food_data(food_log)

# Print Info
print('''Enter:
"y" to accept and add, 
"n" to go to the next item,
"s" to see sidedishes had for a dish,
and "q" to quit,

''')
source_food_log, mapping, side_dishes = flf.suggest_meal_and_update(
    food_data, mapping, side_dishes, DATA_PATH)


def get_col_widths(df):
    # First we find the maximum length of the index column
    idx_max = max([len(str(s)) for s in df.index.values] +
                  [len(str(df.index.name))]) + 2
    # Then, we concatenate this to the max of the lengths of column name and its values for each column, left to right
    return [idx_max] + [max([len(str(s)) + 2 for s in df[col].values] + [len(col)]) for col in df.columns]


def write_data_without_borders(writer, df, sheet_name, **kwargs):
    pd.read_csv(io.StringIO(df.to_csv(**kwargs)), header=None).to_excel(
        writer, sheet_name, header=None, index=None)

    worksheet = writer.sheets[sheet_name]
    for i, width in enumerate(get_col_widths(df)):
        if i == 0 and kwargs.get('index') == False:
            i -= 1
            continue
        worksheet.set_column(i, i, width)


with pd.ExcelWriter(DATA_PATH, datetime_format='YYYY-MM-DD', engine='xlsxwriter') as writer:
    write_data_without_borders(
        writer, source_food_log.rename_axis('Date').rename(columns=lambda x: x.capitalize()), 'food_log')
    write_data_without_borders(
        writer, mapping.rename_axis('entered_name'), 'mapping')
    write_data_without_borders(writer, side_dishes, 'side_dishes', index=False)
    write_data_without_borders(
        writer, food_data, 'food_data')
