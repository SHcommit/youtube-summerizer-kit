# 벤치마크 reference 사람 검토표

> 임시 사람 검토용 문서입니다. 실행 가능한 JSON reference가 아니며, 검토가 끝나면 삭제해도 됩니다.
> 각 원본 영상을 해당 시점 전후로 재생하고, 후보 문장이 원래 발화의 의미·조건·발화자를 보존하는지 확인하세요.
> `승인`, `수정`, `거절` 중 하나를 마지막 열에 기록합니다. AI의 사전 권고는 사람 승인이 아닙니다.
> 아래 근거는 자동자막의 해당 발화를 줄이지 않고 옮긴 것입니다. 자동자막 자체의 오인식 가능성은 영상 음성으로 최종 확인하세요.

## 용어 메모

- **기관 투자자 / institutional trader**: 은행·연기금·자산운용사·헤지펀드처럼 고객이나 조직의 큰 자금을 전문적으로 운용하는 시장 참여자입니다.
- **개인(리테일) 투자자 / retail trader**: 주로 자기 자금으로 거래하는 개인 투자자를 뜻합니다. 단순히 “기관을 제외한 모든 사람”이라는 법적 분류는 아니며, 이 영상에서는 기관 투자자의 거래 방식과 대비되는 일반 개인 거래자를 가리킵니다.
- **stop-loss**: 손실이 일정 수준에 이르면 자동 또는 수동으로 포지션을 정리하려고 정해 둔 가격입니다.
- **a tick under the last low**: 직전 저점보다 호가 단위(tick) 하나 낮은 가격이라는 뜻입니다.

## 1. Anthropic 영어 14분 34초

- 원본: <https://www.youtube.com/watch?v=aBUniZHgCnE>
- 언어 / 길이: 영어 / 14분 34초

| 시점 | 비교할 후보 문장 (한국어) | 원문 자동자막 근거 | AI 사전 권고 | 사람 판정 |
| --- | --- | --- | --- | --- |
| 03:00 | 발표자는 감속이 가능하다면 법·제도·가드레일이 따라잡을 시간을 줄 수 있다고 말한다. | “if it were possible to slow down, so that our laws and our institutions and guardrails that we actually need have time to catch up, it would be a very good thing.” | 승인 | |
| 06:00 | 발표자는 모델이 다음 단어만 예측하는 것이 아니라 세계의 내부 표현을 구축한다고 말한다. | “as these models learn, they're not just predicting the next word. They're building internal representations of the world based on our language and then responding from those representations.” | 승인 | |
| 09:00 | 기만과 편법이 보상되는 훈련에서는 모델에 일반화된 부패가 생길 수 있다고 말한다. | “when deception and cutting corners has been rewarded, the model develops a kind of generalized corruption, a bad character.” | 승인 | |
| 12:00 | 도표에서 파랑은 AI가 이미 수행할 수 있는 일, 빨강은 AI가 실제 수행 중인 일을 뜻한다고 설명한다. | “blue is what AI could feasibly do already. It's actually probably already outdated. Red is what it's doing.” | 승인 | |

## 2. 영어 39분

- 원본: <https://www.youtube.com/watch?v=ZIaOBAjvc38>
- 언어 / 길이: 영어 / 39분

| 시점 | 비교할 후보 문장 (한국어) | 원문 자동자막 근거 | AI 사전 권고 | 사람 판정 |
| --- | --- | --- | --- | --- |
| 00:29 | 발표자는 지금이 창업하기에 세계적으로 가장 좋은 시기가 될 것이라고 전망한다. | “I think this is going to be the best time in the world to do a startup and it's gonna be quite amazing to see.” | 승인 | |
| 01:20 | 발표자는 과거 YC 초기 배치의 각 스타트업이 3개월 걸려 만든 일을 이제 코딩 에이전트가 약 7분에 할 수 있다고 대비한다. | “what took three months to build at the time that each company built over the whole YC startup could now be done with like seven minutes by a coding agent.” | 수정 | |
| 01:42 | 발표자는 현재 스타트업이 전문가들과 함께 이전에는 불가능했던 어려운 기술 문제를 맡을 수 있다고 말한다. | “I can go start the world's most ambitious crazy company. I can have experts in every field working together. I can do these very hard technological things that were just impossible.” | 수정 | |

## 3. 영어 4분 35초

- 원본: <https://www.youtube.com/watch?v=c4GaJKprGEs>
- 언어 / 길이: 영어 / 4분 35초

| 시점 | 비교할 후보 문장 (한국어) | 원문 자동자막 근거 | AI 사전 권고 | 사람 판정 |
| --- | --- | --- | --- | --- |
| 00:09 | 발표자는 stop hunting이 특히 개인(리테일) 투자자에게 부정적으로 인식되는 거래 현상이라고 말한다. | “Is there something called stop hunting that takes place in the trading world? It's always looked upon as negative certainly at the retail trader level.” | 승인 | |
| 00:30 | 발표자는 기관 투자자는 좋은 가격대에서 매수하지만, 많은 개인(리테일) 투자자는 확인 신호를 기다린다고 대비한다. | “Institutional traders are taught from their first day that they buy good levels or they don't buy at all. Unfortunately, most retail traders will wait for some confirmation before they get in.” | 승인 | |
| 00:50 | 발표자는 많은 개인(리테일) 투자자가 stop-loss를 직전 저점보다 호가 한 단위 낮은 가격에 두며, 그 위치가 기관 주문이 있는 지점과 겹친다고 말한다. | “Now, most traders will put their stop loss a tick under the last low and they will invariably put their stop loss at exactly where the institutional orders are.” | 수정 | |

## 4. 영어 55분 48초

- 원본: <https://www.youtube.com/watch?v=XDB5beon4DY>
- 언어 / 길이: 영어 / 55분 48초

| 시점 | 비교할 후보 문장 (한국어) | 원문 자동자막 근거 | AI 사전 권고 | 사람 판정 |
| --- | --- | --- | --- | --- |
| 00:05 | 발표자는 기술 발전이 사람들의 삶을 더 좋게 만들 때에만 진정으로 의미가 있다고 말한다. | “the only way that it really matters is if it makes people's lives like much better than they otherwise would have been.” | 승인 | |
| 00:22 | 발표자는 AI와 관련한 권력 집중이 무서운 일이라고 경고한다. | “but concentration of power with AI is a terrifying thing. I don't think anyone should want to live in a world of AI overlords or company that is the rough equivalent of that.” | 승인 | |
| 01:11 | 발표자는 지난 어려움의 원인을 너무 많은 일을 하면서 충분히 집중하지 못한 데서 찾는다. | “I think we just we're doing too many things. We're not focused enough and they're actually all good things to do, but the trick is we're in this like unbelievable moment in history where you can only do the very few great things. So we spread ourselves too thin.” | 승인 | |

## 5. 한국어 대화 38분 48초

- 원본: <https://www.youtube.com/watch?v=wVJrspYo-18>
- 언어 / 길이: 한국어 / 38분 48초

| 시점 | 비교할 후보 문장 (한국어) | 원문 자동자막 근거 | AI 사전 권고 | 사람 판정 |
| --- | --- | --- | --- | --- |
| 00:23 | 인터뷰이는 살아남는 일의 기준으로 자신의 일이 가치를 부여하는지와 결과를 만들어내는 능력을 든다. | “저는 일에 있어서 기본적으로 살아남는 능력은 이런 거라고 생각을 해요. 내가 하는 일이 가치를 부여하고 있느냐? 결과를 만들어내는 능력. 저는 이 일의 플로우가 핵심 플로우가 그거라고 생각하거든요.” | 수정 | |
| 01:03 | 인터뷰이는 AI 변화 속에서 가장 유리한 계층은 30대라고 생각한다고 말한다. | “모두가 이제 AI로 인한 일자리 위기를 얘기하잖아요. 어떤 직업이든 상관없이 지금 다 흔들리고 있다. 근데 수정님이 보시기에 AI 임팩트 앞에서 가장 위험한 세대랑 가장 유리한 세대는 어디인가요? 제일 유리한 계층은 30대라고 생각이 들어요.” | 승인 | |
| 01:13 | 인터뷰이는 AI 활용 능력만으로는 충분하지 않고 도메인 지식도 필요하다고 말한다. | “하나는 AI를 내가 얼마나 잘 활용하느냐 하는 부분, AI 리터라고 우리가 그랬죠. 이게 필요하죠. 근데 또 하나는 내가 AI 리터만 갖고 있다 그래서 뭐가 되는 게 아니거든요. 그러니까 뭐가 필요하냐면은 도메인 지식이 필요해요.” | 승인 | |

## 6. 한국어 강의 45분 46초

- 원본: <https://www.youtube.com/watch?v=YcA31dmSNMk>
- 언어 / 길이: 한국어 / 45분 46초

| 시점 | 비교할 후보 문장 (한국어) | 원문 자동자막 근거 | AI 사전 권고 | 사람 판정 |
| --- | --- | --- | --- | --- |
| 00:36 | 발표자는 AI가 지식을 알려 주고 설명하는 일을 자신보다 훨씬 잘한다고 말한다. | “이제 AI가 작년부터 너무 성능이 좋아졌잖아요. 그래서 사실 지식을 알려주고 설명하는 게 AI가 훨씬 더 잘하더라고요.” | 승인 | |
| 00:59 | 발표자는 인간이 AI와 협력하면 더 똑똑해질 수 있는 경험을 만들 수 있기를 바란다고 말한다. | “AI 자체가 이미 똑똑한데 사람인 우리가 AI만큼 혹은 AI랑 같이 협력해 가지고 사람도 더 똑똑해질 수 있는 경험들을 더 많이 만들어 보면 교육자로서 더 의미 있는 경험들을 할 수 있지 않을까 싶어 가지고.” | 수정 | |
| 01:07 | 발표자는 인간과 LLM이 협력해 사람이 더 똑똑해지기까지의 시행착오를 오늘 이야기의 주제로 제시한다. | “그래서 오늘은 인간과 LLM이 협력해서 사람이 더 똑똑해지기 위해서 어떤 시행착오를 겪었는지에 대한 이야기들로 아마 이어질 것 같아요.” | 승인 | |

## 검토 결과 전달 형식

예시: `한국어 강의: 1 승인, 2 승인, 3 수정(표현: 새 문장)`.

모든 선택이 확정되면 승인 항목만 별도 JSON reference로 전사합니다. 수정·거절 항목은 전사하지 않습니다.
