package com.catastrophe.controller;

import com.catastrophe.model.AnalyseResult;
import com.catastrophe.model.AnalysisEntity;
import com.catastrophe.repository.AnalysisRepository;
import com.catastrophe.service.AnalyseService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.support.RedirectAttributes;
import java.util.Base64;

@Controller
public class AnalyseController {

  @Autowired
  private AnalyseService analyseService;

  @Autowired
  private AnalysisRepository analysisRepository;

  @GetMapping("/")
  public String index() {
    return "index";
  }

  @PostMapping("/analyser")
  public String analyserImage(
    @RequestParam("image") MultipartFile image,
    @RequestParam(value = "gouvernorat", defaultValue = "Tunis") String gouvernorat,
    RedirectAttributes redirectAttributes) {

    try {
      AnalyseResult result = analyseService.analyserImage(image, gouvernorat);
      redirectAttributes.addFlashAttribute("result", result);
      redirectAttributes.addFlashAttribute("imageBase64",
        Base64.getEncoder().encodeToString(image.getBytes()));
    } catch (Exception e) {
      redirectAttributes.addFlashAttribute("error", e.getMessage());
    }

    return "redirect:/resultat";
  }
  @GetMapping("/resultat")
  public String resultat() {
    return "resultat";
  }

  @GetMapping("/historique")
  public String historique(Model model) {
    model.addAttribute("analyses", analysisRepository.findAll());
    return "historique";
  }
}
