package com.catastrophe.service;

import com.catastrophe.model.AnalyseResult;
import com.catastrophe.model.AnalysisEntity;
import com.catastrophe.repository.AnalysisRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;

@Service
public class AnalyseService {

  @Autowired
  private AnalysisRepository analysisRepository;

  private final RestTemplate restTemplate = new RestTemplate();

  public AnalyseResult analyserImage(MultipartFile image, String gouvernorat) throws IOException {
    // Appel à FastAPI
    HttpHeaders headers = new HttpHeaders();
    headers.setContentType(MediaType.MULTIPART_FORM_DATA);

    MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
    body.add("file", new ByteArrayResource(image.getBytes()) {
      @Override
      public String getFilename() {
        return image.getOriginalFilename();
      }
    });

    HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);

    ResponseEntity<AnalyseResult> response = restTemplate.exchange(
      "http://localhost:8000/analyze",
      HttpMethod.POST,
      requestEntity,
      AnalyseResult.class
    );

    AnalyseResult result = response.getBody();

    if (result != null && result.isSuccess()) {
      // Calcul du montant
      double montant = 1000 + (result.getGravite() - 1) * 12250;
      result.setMontant_estime(montant);

      // Sauvegarde en base de données (PERMANENT)
      AnalysisEntity entity = new AnalysisEntity();
      entity.setImageName(image.getOriginalFilename());
      entity.setGravite(result.getGravite());
      entity.setConseil(result.getConseil());
      entity.setNbObjets(result.getNb_objets());
      entity.setMontantEstime(montant);
      analysisRepository.save(entity);

      System.out.println("✅ Analyse sauvegardée en base avec ID: " + entity.getId());
    }

    return result;
  }
}
