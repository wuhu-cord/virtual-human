package com.example.ai.controller;

import com.alibaba.fastjson.JSONObject;
import com.example.ai.service.AIService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@Slf4j
@RestController
@CrossOrigin
public class TestController {

    @Autowired
    private AIService aiService;

    // 核心接口：前端发送消息，返回AI回答+数字人视频地址
    @PostMapping("/AI")
    public JSONObject chat(@RequestBody JSONObject requestBody) {
        JSONObject result = new JSONObject();
        try {
            // 1. 获取用户消息
            String message = requestBody.getString("message");
            log.info("收到用户消息：{}", message);

            // 2. AI对话
            String aiReply = aiService.aiChat(message);
            if (aiReply.contains("异常")) {
                result.put("code", 500);
                result.put("msg", aiReply);
                return result;
            }
            result.put("aiReply", aiReply);

            // 3. TTS语音生成
            String audioFilename = aiService.textToAudio(aiReply);
            if (audioFilename == null) {
                result.put("code", 500);
                result.put("msg", "语音生成失败，请检查TTS服务");
                return result;
            }

            // 4. 数字人视频生成
            String videoLocalPath = aiService.generateAvatarVideo(audioFilename);
            if (videoLocalPath == null) {
                result.put("code", 500);
                result.put("msg", "视频生成失败，请检查duix服务");
                return result;
            }

            // 5. 转成前端可访问的URL
            String videoUrl = aiService.getVideoAccessUrl(videoLocalPath);
            result.put("code", 200);
            result.put("videoUrl", videoUrl);
            log.info("处理完成，视频地址：{}", videoUrl);
            return result;

        } catch (Exception e) {
            log.error("处理异常", e);
            result.put("code", 500);
            result.put("msg", "系统异常：" + e.getMessage());
            return result;
        }
    }
}