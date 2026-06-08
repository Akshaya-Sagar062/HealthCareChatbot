from flask import Flask, render_template, request, redirect, url_for, session import pandas as pd
from sklearn.tree import DecisionTreeClassifier from sklearn.preprocessing import LabelEncoder import os
app = Flask( name ) app.secret_key = "your_secret_key"

#
# USER DATA HANDLING #
USER_CSV = "users.csv"
if not os.path.exists(USER_CSV):
pd.DataFrame(columns=["username", "password"]).to_csv(USER_CSV, index=False)
def get_users():
return pd.read_csv(USER_CSV)
def save_user(username, password): users = get_users()
users = pd.concat(
[users, pd.DataFrame({"username": [username], "password": [password]})], ignore_index=True
)
users.to_csv(USER_CSV, index=False)
#
# LOAD HEALTH DATA #

TRAINING_CSV = "Training.csv" DOCTORS_CSV = "doctors_dataset.csv" GUIDELINES_CSV = "disease_guidelines.csv"
training_df = pd.read_csv(TRAINING_CSV) doctors_df = pd.read_csv(DOCTORS_CSV)
SYMPTOM_COLS = [col for col in training_df.columns if col != "prognosis"] X = training_df[SYMPTOM_COLS]
 
y = training_df["prognosis"]
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)

model = DecisionTreeClassifier( max_depth=6, min_samples_leaf=5, random_state=42
)
model.fit(X, y_encoded)

#
# GUIDELINES LOADING #
def split_to_list(val): if pd.isna(val):
return []
text = str(val).strip() if ";" in text:
return [x.strip() for x in text.split(";") if x.strip()] if "," in text:
return [x.strip() for x in text.split(",") if x.strip()] return [text]
def normalize(text):
return str(text).strip().lower() guidelines_map = {}
if os.path.exists(GUIDELINES_CSV):
guidelines_df = pd.read_csv(GUIDELINES_CSV) for _, row in guidelines_df.iterrows():
guidelines_map[normalize(row["disease"])] = { "dos": split_to_list(row.get("dos", "")),
"donts": split_to_list(row.get("donts", "")),
"measures": split_to_list(row.get("immediate_actions", "")), "medicines": split_to_list(row.get("otc_suggestions", ""))
}
#
# PREDICTION FUNCTION #
def predict_from_vector(vector): encoded_pred = model.predict([vector])[0]
disease = label_encoder.inverse_transform([encoded_pred])[0] confidence = float(model.predict_proba([vector])[0].max())
 

symptoms_present = [
SYMPTOM_COLS[i] for i, v in enumerate(vector) if v == 1
]

# LOW CONFIDENCE SAFETY
if confidence < 0.4: disease = "Uncertain"
doctor_name = "Consult a General Physician" doctor_link = "#"
g = {"dos": [], "donts": [], "measures": [], "medicines": []} else:
# DOCTOR MATCHING (case-insensitive) doctor_row = doctors_df[
doctors_df["Disease"].str.lower() == disease.lower()
]
if not doctor_row.empty:
doctor_name = doctor_row["Name"].values[0] doctor_link = doctor_row["Link"].values[0]
else:
doctor_name = "No doctor found" doctor_link = "#"
# GUIDELINES MATCHING
g = guidelines_map.get(normalize(disease), {
"dos": [], "donts": [], "measures": [], "medicines": []
})

return {
"disease": disease, "confidence": confidence,
"symptoms_present": symptoms_present, "doctor_name": doctor_name, "doctor_link": doctor_link,
"dos": g["dos"],
"donts": g["donts"],
"measures": g["measures"], "medicines": g["medicines"]
}
#
# ROUTES #
@app.route("/", methods=["GET", "POST"]) def login():
if session.get("user"):
return redirect(url_for("home"))
 

error = None
if request.method == "POST":
username = request.form.get("username") password = request.form.get("password") users = get_users()

if username not in users["username"].values: error = "User not found. Please register first."
else:
if password == users[users["username"] == username]["password"].values[0]: session["user"] = username
return redirect(url_for("home")) else:
error = "Incorrect password."
return render_template("login.html", error=error)

@app.route("/register", methods=["GET", "POST"]) def register():
if session.get("user"):
return redirect(url_for("home"))
message = error = None
if request.method == "POST":
username = request.form.get("username") password = request.form.get("password") users = get_users()
if username in users["username"].values: error = "Username already exists."
else:
save_user(username, password)
message = "Account created successfully! Please login."
return render_template("register.html", message=message, error=error) @app.route("/logout")
def logout(): session.pop("user", None)
return redirect(url_for("login"))

@app.route("/home") def home():
if not session.get("user"):
return redirect(url_for("login"))
return render_template("index.html", symptoms=SYMPTOM_COLS)
@app.route("/predict", methods=["POST"])
 
def predict():
if not session.get("user"):
return redirect(url_for("login")) symptom_dict = request.form
if not any(int(symptom_dict.get(col, 0)) for col in SYMPTOM_COLS): session["warning"] = "⚠ Please select at least one symptom."
return redirect(url_for("home"))
vector = [int(symptom_dict.get(col, 0)) for col in SYMPTOM_COLS] session["prediction_result"] = predict_from_vector(vector)
return redirect(url_for("result_page"))
@app.route("/result") def result_page():
if "prediction_result" not in session: return redirect(url_for("home"))
return render_template("result.html", data=session["prediction_result"])
#
if  name	== " main ": app.run(debug=True)
