import random
import pandas as pd

random.seed(42)

df = pd.read_csv("all_images.csv", sep = " ")

columns = [
    column_name
    for column_name in df.columns.to_list()
    if column_name != "Image"
]
df[columns] = df[columns].astype(bool).copy()

df = df[~df["Blurry"]].copy()

df.drop(
    columns = [
        "Blurry",
        "5_o_Clock_Shadow",
        "Attractive",
        "Male",
        "Mouth_Slightly_Open",
        "Smiling",
        "Young"
    ],
    inplace = True
)

straight_hair = df[df["Straight_Hair"]].copy()
# with open("straight_hair.txt", "w") as file:
#     for img in straight_hair["Image"]:
#         file.write(img)
#         file.write("\n")

df = df[~df.index.isin(straight_hair.index)].copy()
df.drop(
    columns = ["Straight_Hair"],
    inplace = True
)

accumulated_df = pd.DataFrame()
special_index = df[df["Wavy_Hair"]].index.to_list()
special_index = random.sample(special_index, 12221)
special_df = df[df.index.isin(special_index)].copy()
accumulated_df = pd.concat([accumulated_df, special_df]).copy()

extra_columns = [
    column_name
    for column_name in df.columns.to_list()
        if (column_name != "Image") and (column_name != "Wavy_Hair")
]
for column_name in extra_columns:
    extra_index = df[df[column_name]].index.to_list()
    extra_index = random.sample(extra_index, 920)
    extra_df = df[df.index.isin(extra_index)].copy()

    accumulated_df = pd.concat([accumulated_df, extra_df]).copy()

# with open("no_straight_hair.txt", "w") as file:
#     for img in accumulated_df["Image"]:
#         file.write(img)
#         file.write("\n")
