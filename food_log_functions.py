from datetime import datetime
import pandas as pd


def get_food_log(file_path, sheet_name='food_log'):
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
    except (FileNotFoundError, ValueError):
        df = pd.DataFrame(
            columns=['date', 'day', 'breakfast', 'lunch', 'dinner'])
    df.rename(columns=lambda x: x.lower(), inplace=True)
    # `index_col` raises a ValueError, ask on SO
    df.set_index('date', inplace=True)
    return (df['breakfast']
            .append(df['lunch'])
            .append(df['dinner'])
            .to_frame(name='food_item')
            )


def guess_combo(item):
    combo_guess = None
    for sep in ['/', '+']:
        if sep in item:
            splitted = item.title().split(sep)
            meal, side_dish = splitted[0].strip(), splitted[1:]
            side_dish = ' + '.join(x.title().strip()
                                   for x in side_dish).strip()
            combo_guess = ' / '.join([meal, side_dish])
            break
    if not combo_guess:
        combo_guess = item.title()
    return combo_guess


def get_meal_and_side_dish(combo):
    try:
        meal, side_dish = combo.split(' / ')
    except ValueError:
        meal = combo
        side_dish = None
    return meal, side_dish


def update_side_dishes(
    item,
    side_dish,
    side_dishes_df
):
    # All side dishes are seperated by a plus sign
    for side_dish_part in side_dish.split('+'):
        # Remove unnecessary whitespace
        side_dish_part = side_dish_part.strip()
        if item in side_dishes_df.columns:
            if side_dish not in side_dishes_df[item]:
                # Set side dish to where the row number is the length of non NA rows for this item
                side_dishes_df.loc[len(side_dishes_df[item].dropna()),
                                   item] = side_dish_part
        else:
            # Create a blank column, and add the side dish to the first row in it
            side_dishes_df[item] = None
            side_dishes_df.loc[0, item] = side_dish_part
    return side_dishes_df


def get_updated_mapping(
    df,
    file_path,
    mapping_index_col,
    food_item_col,
    sheet_name='mapping',
    side_dish_sheet_name='side_dishes',
    banned_items=None,
):
    if banned_items is None:
        banned_items = []

    try:
        mapping = pd.read_excel(
            file_path, sheet_name=sheet_name, index_col=mapping_index_col)
        side_dishes = pd.read_excel(
            file_path, sheet_name=side_dish_sheet_name)
    except (FileNotFoundError, ValueError):
        mapping = pd.DataFrame(
            columns=['actual_name']).rename_axis('entered_name')
        side_dishes = pd.DataFrame()

    if mapping.columns.empty:
        mapping = pd.DataFrame(
            columns=['actual_name']).rename_axis('entered_name')

    # Check that not all of the food items are already in mapping
    if not all(x in mapping.index or x in banned_items for x in df[food_item_col].dropna()):
        # Print info
        print(f'Enter the name of this meal along with it\'s sidedish '
              'seperated by a forward slash (\'Idly / Coconut Chutney\') '
              'or just the name (\'Idly\') if there\'s no name. Enter a blank '
              'if you want to choose the default (the default will be displayed in brackets)\n\n')
        for item in df[food_item_col].dropna():
            # Make sure that item isn't in mapping and isn't NA
            if item in mapping.index or item in banned_items:
                continue

            # Guess main item and side dish
            combo_guess = guess_combo(item)

            # Get the mapping value, or combo_guess if none is provided,
            # and get meal and side dish from it
            combo = input(
                f'Give the name for {item} (default {combo_guess})\n') or combo_guess
            if combo == 'q':
                return mapping, side_dishes
            meal, side_dish = get_meal_and_side_dish(combo)

            # Set meal to item in mapping, and set side dishes to item
            mapping.loc[item] = (meal,)
            if side_dish:
                side_dishes = update_side_dishes(meal, side_dish, side_dishes)
    return mapping, side_dishes


def cleanup_food_log(food_log, mapping, banned_items=None):
    if banned_items is None:
        banned_items = ['OUT']

    # Replace long names with combos in the mapping
    food_log = food_log.replace(
        dict(zip(mapping.index, mapping.actual_name)))

    # Remove all instances of banned items
    food_log = food_log[~food_log.food_item.isin(banned_items)]
    return food_log


def get_food_data(food_log):
    food_data = food_log.food_item.value_counts().to_frame().rename_axis('food_item')
    print(food_data)
    food_data.columns = ['times_had']

    # Set the last had column to the most recent date in `food_log` for each item
    food_data['last_had'] = [food_log[food_log.food_item == item].index.max()
                             for item in food_data.index]
    food_data = food_data.sort_values(
        ['last_had', 'times_had'], na_position='first')
    return food_data


def selective_input(q, options=None):
    if options is None:
        options = ['y', 'n', 's', 'q']
    answer = input(q)
    while answer.lower() not in options:
        answer = input('That was not among the expected answers. ' + q)
    return answer.lower()


def suggest_meal_and_update(food_data, mapping, side_dishes, source_file_path, source_file_sheet='food_log'):
    source_food_log = pd.read_excel(
        source_file_path, sheet_name=source_file_sheet, index_col='Date')
    for item in food_data.index.unique():
        answer = selective_input(
            f'Do you want to have {item} for the next meal?\n')
        while answer == 's':
            print_side_dishes(item, side_dishes)
            answer = selective_input(
                f'Do you want to have {item} for the next meal?\n')
        if answer == 'q':
            print('Quiting')
            return source_food_log, mapping, side_dishes
        elif answer == 'y':
            print(
                f'What side dishes will you have with item (seperated by +, blank for nothing)?')
            print_side_dishes(item, side_dishes)
            side_dish = input()
            if side_dish:
                side_dishes = update_side_dishes(item, side_dish, side_dishes)
                item = f'{item} / {side_dish}'
            # Update mapping
            mapping.loc[item] = item

            meal = selective_input(f'What meal will you have {item} for?\n', [
                'breakfast', 'lunch', 'dinner'])
            # Update log
            today = datetime.now().strftime('%Y-%m-%d')

            source_food_log.loc[today, meal] = item
            source_food_log.loc[today, 'day'] = datetime.now().strftime('%A')
            break
    return source_food_log, mapping, side_dishes


def print_side_dishes(item, side_dishes):
    try:
        print(
            f'{item} has previously been eaten with {", ".join(side_dishes[item].dropna()) or "nothing"}')
    except KeyError:
        print(f'{item} previously has been eaten with nothing')
