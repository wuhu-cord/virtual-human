package com.example.ai.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class WebConfig implements WebMvcConfigurer {

    // 全局跨域配置（局域网访问必备）
    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/**")
                .allowedOriginPatterns("*")
                .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
                .allowCredentials(true)
                .maxAge(3600);
    }

    // 映射本地视频目录到前端可访问的URL
    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        // 前端访问 /video/** 就能访问到 d:/duix_avatar_data/face2face/ 里的所有文件
        registry.addResourceHandler("/video/**")
                .addResourceLocations("file:d:/duix_avatar_data/face2face/");
    }
}
