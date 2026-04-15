from fastapi import FastAPI, File, UploadFile, Form
from ultralytics import YOLO
import cv2
import numpy as np
import uvicorn
from fastapi.responses import JSONResponse
import base64

app = FastAPI(title="Service IA Catastrophes Naturelles")

# Charger le modèle YOLO entraîné
model = YOLO("C:/Users/x/runs/detect/train3/weights/best.pt")

# ============================================
# COEFFICIENTS GÉOGRAPHIQUES (TUNISIE)
# ============================================
COEFFICIENTS_GOUVERNORATS = {
    # Zone 1 : Grand Tunis (coût élevé)
    "Tunis": 1.2,
    "Ariana": 1.2,
    "Ben Arous": 1.2,
    "La Manouba": 1.2,
    
    # Zone 2 : Grandes villes côtières
    "Sfax": 1.1,
    "Sousse": 1.1,
    "Nabeul": 1.1,
    "Monastir": 1.1,
    "Mahdia": 1.1,
    
    # Zone 3 : Villes moyennes
    "Bizerte": 1.0,
    "Béja": 1.0,
    "Jendouba": 1.0,
    "Zaghouan": 1.0,
    
    # Zone 4 : Zones rurales
    "Le Kef": 0.9,
    "Siliana": 0.9,
    "Kairouan": 0.9,
    "Kasserine": 0.85,
    "Sidi Bouzid": 0.85,
    
    # Zone 5 : Sud
    "Gabès": 0.85,
    "Médenine": 0.85,
    "Tataouine": 0.8,
    "Tozeur": 0.8,
    "Gafsa": 0.85,
    "Kébili": 0.8,
}

def get_coefficient_gouvernorat(gouvernorat: str) -> float:
    """Retourne le coefficient pour un gouvernorat donné"""
    return COEFFICIENTS_GOUVERNORATS.get(gouvernorat, 0.9)

# ============================================
# 1. DÉTECTION DE FEU PAR COULEUR
# ============================================
def detect_fire_by_color(image):
    """Retourne gravité (0-3) basée sur le pourcentage de pixels rouges/orange"""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 100, 100])
    upper_red2 = np.array([179, 255, 255])
    
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = cv2.bitwise_or(mask1, mask2)
    
    fire_pixels = cv2.countNonZero(mask)
    total_pixels = image.shape[0] * image.shape[1]
    ratio = fire_pixels / total_pixels
    
    if ratio > 0.40:
        return 3
    elif ratio > 0.25:
        return 2
    elif ratio > 0.10:
        return 1
    else:
        return 0

# ============================================
# 2. DÉTECTION D'INONDATION PAR COULEUR
# ============================================
def detect_flood_by_color(image):
    """Retourne gravité (0-3) basée sur le pourcentage de pixels bleus"""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    lower_blue = np.array([90, 50, 50])
    upper_blue = np.array([130, 255, 255])
    mask = cv2.inRange(hsv, lower_blue, upper_blue)
    
    blue_pixels = cv2.countNonZero(mask)
    total_pixels = image.shape[0] * image.shape[1]
    ratio = blue_pixels / total_pixels
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    bright_pixels = cv2.countNonZero(cv2.inRange(gray, 200, 255))
    bright_ratio = bright_pixels / total_pixels
    has_reflection = bright_ratio > 0.15
    
    gravite = 0
    if ratio > 0.50:
        gravite = 3
    elif ratio > 0.30:
        gravite = 2
    elif ratio > 0.15:
        gravite = 1
    
    if has_reflection and gravite > 0:
        gravite = min(3, gravite + 1)
    
    return gravite

# ============================================
# 3. DÉTECTION DE FUMÉE PAR COULEUR + TEXTURE
# ============================================
def detect_smoke(image):
    """Retourne gravité (0-3) basée sur pixels gris et texture"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    smoke_pixels = cv2.countNonZero(cv2.inRange(gray, 150, 200))
    total_pixels = image.shape[0] * image.shape[1]
    ratio = smoke_pixels / total_pixels
    
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    laplacian = cv2.Laplacian(blur, cv2.CV_64F)
    variance = np.var(laplacian)
    has_texture = variance > 500
    
    gravite = 0
    if ratio > 0.40 and has_texture:
        gravite = 3
    elif ratio > 0.20 and has_texture:
        gravite = 2
    elif ratio > 0.10:
        gravite = 1
    
    return gravite

# ============================================
# 4. DÉTECTION D'OBJETS ALLONGÉS (ARBRE TOMBÉ)
# ============================================
def detect_fallen_objects(results, img_height):
    if results[0].boxes is None:
        return 0
    
    gravite = 0
    for box in results[0].boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        width = x2 - x1
        height = y2 - y1
        center_y = (y1 + y2) / 2
        
        if width > height * 2 and center_y > img_height * 0.7:
            gravite = max(gravite, 3)
    
    return gravite

# ============================================
# 5. DÉTECTION D'ACCIDENT (VOITURES PROCHES)
# ============================================
def detect_accident(results):
    if results[0].boxes is None:
        return 0
    
    cars = []
    for box in results[0].boxes:
        classe_id = int(box.cls[0])
        classe_nom = model.names[classe_id]
        if classe_nom == "car":
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            cars.append({
                'center_x': (x1 + x2) / 2,
                'center_y': (y1 + y2) / 2
            })
    
    gravite = 0
    for i in range(len(cars)):
        for j in range(i + 1, len(cars)):
            dx = cars[i]['center_x'] - cars[j]['center_x']
            dy = cars[i]['center_y'] - cars[j]['center_y']
            distance = (dx**2 + dy**2)**0.5
            
            if distance < 50:
                gravite = max(gravite, 4)
            elif distance < 100:
                gravite = max(gravite, 3)
    
    return gravite

# ============================================
# 6. GRAVITÉ BASE YOLO
# ============================================
def get_base_gravity(results):
    nb_objets = len(results[0].boxes) if results[0].boxes is not None else 0
    
    if nb_objets == 0:
        return 1
    elif nb_objets < 3:
        return 2
    elif nb_objets < 6:
        return 3
    elif nb_objets < 10:
        return 4
    else:
        return 5

# ============================================
# 7. CALCUL DE LA GRAVITÉ FINALE
# ============================================
def calculate_final_gravity(image, results):
    img_height = image.shape[0]
    
    gravite_feu = detect_fire_by_color(image)
    gravite_eau = detect_flood_by_color(image)
    gravite_fumee = detect_smoke(image)
    gravite_objet = detect_fallen_objects(results, img_height)
    gravite_accident = detect_accident(results)
    gravite_base = get_base_gravity(results)
    
    gravite_feu_5 = {0:0, 1:2, 2:3, 3:5}[gravite_feu]
    gravite_eau_5 = {0:0, 1:2, 2:3, 3:4}[gravite_eau]
    gravite_fumee_5 = {0:0, 1:2, 2:3, 3:4}[gravite_fumee]
    
    gravites = [gravite_base, gravite_feu_5, gravite_eau_5, gravite_fumee_5, gravite_objet, gravite_accident]
    gravite_finale = max(gravites)
    
    nb_catastrophes = sum([1 for g in [gravite_feu, gravite_eau, gravite_fumee] if g > 0])
    if nb_catastrophes >= 2 and gravite_finale < 5:
        gravite_finale = min(5, gravite_finale + 1)
    
    return gravite_finale

# ============================================
# 8. GÉNÉRATION DE LA CARTE THERMIQUE
# ============================================
def generate_heatmap(image, results):
    heatmap = np.zeros((image.shape[0], image.shape[1]), dtype=np.float32)
    
    if results[0].boxes is not None:
        for box in results[0].boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            classe_id = int(box.cls[0])
            classe_nom = model.names[classe_id]
            
            poids = {"person": 0.5, "car": 0.3, "fire hydrant": 0.8, "smoke": 0.9}.get(classe_nom, 0.1)
            heatmap[y1:y2, x1:x2] += poids
    
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    lower_red = np.array([0, 100, 100])
    upper_red = np.array([10, 255, 255])
    red_mask = cv2.inRange(hsv, lower_red, upper_red)
    heatmap += (red_mask / 255) * 0.8
    
    lower_blue = np.array([90, 50, 50])
    upper_blue = np.array([130, 255, 255])
    blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
    heatmap += (blue_mask / 255) * 0.6
    
    heatmap = np.clip(heatmap, 0, 1) * 255
    heatmap = heatmap.astype(np.uint8)
    heatmap_colored = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
    overlay = cv2.addWeighted(image, 0.5, heatmap_colored, 0.5, 0)
    
    return overlay, heatmap

# ============================================
# 9. GÉNÉRATION DE L'EXPLICATION TEXTUELLE
# ============================================
def generate_explanation(image, results):
    score_feu = detect_fire_by_color(image)
    score_eau = detect_flood_by_color(image)
    score_fumee = detect_smoke(image)
    
    pourcent_feu = {3: 95, 2: 70, 1: 40, 0: 0}[score_feu]
    pourcent_eau = {3: 90, 2: 65, 1: 35, 0: 0}[score_eau]
    pourcent_fumee = {3: 85, 2: 60, 1: 30, 0: 0}[score_fumee]
    
    criteres = []
    explication_parts = []
    
    if pourcent_feu > 30:
        criteres.append({"type": "feu", "poids": pourcent_feu})
        explication_parts.append(f"Feu détecté ({pourcent_feu}%)")
    if pourcent_eau > 30:
        criteres.append({"type": "inondation", "poids": pourcent_eau})
        explication_parts.append(f"Eau détectée ({pourcent_eau}%)")
    if pourcent_fumee > 30:
        criteres.append({"type": "fumée", "poids": pourcent_fumee})
        explication_parts.append(f"Fumée détectée ({pourcent_fumee}%)")
    
    nb_objets = len(results[0].boxes) if results[0].boxes is not None else 0
    if nb_objets > 5:
        criteres.append({"type": "objets anormaux", "poids": min(90, nb_objets * 10)})
        explication_parts.append(f"{nb_objets} objets détectés")
    
    if not criteres:
        explication = "Aucun critère de catastrophe détecté. Situation normale."
    else:
        explication = " + ".join(explication_parts) + " → gravité "
    
    return explication, criteres

# ============================================
# 10. ENDPOINT API (AVEC COEFFICIENT GÉOGRAPHIQUE)
# ============================================
@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    gouvernorat: str = Form("Tunis")  # PARAMÈTRE GÉOGRAPHIQUE
):
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return JSONResponse(status_code=400, content={"success": False, "error": "Image invalide"})
        
        results = model(img)
        
        objets_detectes = []
        if results[0].boxes is not None:
            for box in results[0].boxes:
                classe_id = int(box.cls[0])
                classe_nom = model.names[classe_id]
                if classe_nom not in objets_detectes:
                    objets_detectes.append(classe_nom)
        
        gravite_finale = calculate_final_gravity(img, results)
        
        heatmap_img, heatmap_data = generate_heatmap(img, results)
        explication, criteres = generate_explanation(img, results)
        
        _, buffer = cv2.imencode('.jpg', heatmap_img)
        heatmap_base64 = base64.b64encode(buffer).decode('utf-8')
        
        conseils = {
            1: "Situation normale. Aucune anomalie detectee.",
            2: "Surveillance recommandee. Restez attentif.",
            3: "Attention : Danger potentiel detecte.",
            4: "Danger eleve : Preparez-vous a evacuer.",
            5: "URGENT : Evacuez immediatement !"
        }
        conseil = conseils.get(gravite_finale, "Situation inconnue.")
        
        # ============================================
        # CALCUL DU MONTANT AVEC COEFFICIENT GÉOGRAPHIQUE
        # ============================================
        montant_base = 1000 + (gravite_finale - 1) * 15000
        coefficient = get_coefficient_gouvernorat(gouvernorat)
        montant_ajuste = round(montant_base * coefficient)
        
        return {
            "success": True,
            "gravite": gravite_finale,
            "conseil": conseil,
            "nb_objets": len(results[0].boxes) if results[0].boxes is not None else 0,
            "objets_detectes": objets_detectes[:10],
            "montant_base": montant_base,
            "montant_estime": montant_ajuste,
            "coefficient": coefficient,
            "gouvernorat": gouvernorat,
            "heatmap": heatmap_base64,
            "explication": explication,
            "criteres": criteres,
            "details": {
                "feu_detecte": detect_fire_by_color(img) > 0,
                "inondation_detectee": detect_flood_by_color(img) > 0,
                "fumee_detectee": detect_smoke(img) > 0
            }
        }
    
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

# ============================================
# 11. LANCEMENT
# ============================================
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)