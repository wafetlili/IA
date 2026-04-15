package com.catastrophe.model;

import lombok.Data;
import java.util.List;
import java.util.Map;

@Data
public class AnalyseResult {
    private boolean success;
    private int gravite;
    private String conseil;
    private int nb_objets;
    private List<String> objets_detectes;
    private Double montant_estime;
    
    // NOUVEAUX CHAMPS POUR L'AFFICHAGE COMPLET
    private Double montant_base;
    private Double coefficient;
    private String gouvernorat;
    private String heatmap;          // image en base64
    private String explication;
    private List<Map<String, Object>> criteres;
    private Map<String, Boolean> details;
}