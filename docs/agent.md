これまでの議論（動的スキーマ、特注品対応、リトライ制限、そして「可能性ヒント」による出口戦略）を全て反映した、**Ojoya AIエージェントの最終設計仕様書**です。

開発チームへの共有資料としてそのままお使いいただける形式でまとめました。

---

# Ojoya AI Valuation Agent - Architecture Specification

## 1. 全体ワークフロー図 (Mermaid)

この図は、画像入力から「確定査定」「概算＋可能性提示」「特注品対応」「エラー」に至るすべてのステートマシンを表しています。

```mermaid
graph TD
    %% --- スタイル定義 ---
    classDef vision fill:#e1bee7,stroke:#4a148c,stroke-width:2px,color:black;
    classDef search fill:#bbdefb,stroke:#0d47a1,stroke-width:2px,color:black;
    classDef logic fill:#c8e6c9,stroke:#1b5e20,stroke-width:2px,color:black;
    classDef user fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,stroke-dasharray: 5 5,color:black;
    classDef endstate fill:#546e7a,stroke:#263238,stroke-width:2px,color:white;
    classDef hint fill:#ffecb3,stroke:#ff6f00,stroke-width:3px,color:black;
    classDef guard fill:#ffcdd2,stroke:#b71c1c,stroke-width:2px,color:black;

    %% --- Phase 0: 初期化 ---
    Start([ユーザー: 画像アップロード]) --> InitCount{Retry = 0}
    InitCount --> NodeA_Init

    %% --- Phase 1: 分類とガードレール ---
    subgraph Phase1 [Phase 1: Classification & Guardrails]
        NodeA_Init(Node A: 初期画像分析):::vision
        NodeA_Init --> CheckType{カテゴリ判定}

        %% A. ガードレール
        CheckType -- "人物/生物/現金" --> GuardRail[対象外判定]:::guard
        GuardRail --> End_Guard(["エラー: 査定対象外です"]):::endstate

        %% B. 特定不可 (Retry Max 5)
        CheckType -- "不明/ピンボケ" --> RetryCheck{Retry < 5 ?}:::logic
        RetryCheck -- Yes --> CountUp[Retry + 1]:::logic
        CountUp --> AskReshoot[再撮影依頼 & ヒント提示]:::user
        AskReshoot --> NodeA_Init
        RetryCheck -- No --> End_GiveUp(["エラー: 特定不能として終了"]):::endstate
    end

    %% --- Phase 2: 特注品フロー (Human-in-the-Loop) ---
    subgraph Phase2 [Phase 2: Unique / Hand-made Flow]
        CheckType -- "特注品/工芸品" --> ExtractFeat(Node A: 構成要素抽出):::vision
        ExtractFeat --> ShowDraft[ドラフト提示 & ユーザー補正フォーム]:::user
        ShowDraft -->|ユーザー入力確定| NodeB_Proxy(Node B: 素材・類似スペック検索):::search
        NodeB_Proxy --> End_Unique(["推定価値提示 (類似品ベース)"]):::endstate
    end

    %% --- Phase 3: 既製品フロー (Dynamic Focus & Hint) ---
    subgraph Phase3 [Phase 3: Mass Product Flow]
        CheckType -- "既製品/流通品" --> NodeB_Broad(Node B: 市場調査 & 要因特定):::search
        NodeB_Broad --> NodeC_Schema(Node C: チェックリスト生成):::logic
        
        %% 質問ループ初期化
        NodeC_Schema --> InitQCount{Q_Count = 0}:::logic
        InitQCount --> NodeA_Targeted(Node A: 詳細変数チェック):::vision
        
        %% 特定判定
        NodeA_Targeted --> CheckSpec{全変数が<br>特定できたか?}:::logic
        
        %% Route A: 完全特定
        CheckSpec -- Yes --> NodeB_Final(Node B: 確定価格検索):::search
        NodeB_Final --> End_Exact(["A. 確定査定額の提示"]):::endstate
        
        %% Route B: 未特定 (質問ループ Max 2)
        CheckSpec -- No --> CheckQCount{Q_Count < 2 ?}:::logic
        
        %% B-1: 質問継続
        CheckQCount -- Yes --> Q_CountUp[Q_Count + 1]:::logic
        Q_CountUp --> AskUser["ユーザーへ選択肢提示<br>(右下のマークは？)"]:::user
        AskUser -->|回答受信| NodeA_Targeted
        
        %% B-2: 質問終了 -> ヒント提示
        CheckQCount -- No --> CalcPotential(最大/最小シナリオ算出):::logic
        CalcPotential --> End_Hint(["B. 概算額 + 『もし〜なら高額』ヒント提示"]):::hint
    end

```

---

## 2. フェーズ別 詳細ロジック仕様

### Phase 1: ガードレールとリトライ

「無駄な処理を省き、リスクを回避する」フェーズです。

* **対象外判定**: 人物の顔、動物、現金、クレジットカード等が写っている場合、即座に終了します（プライバシー/コンプライアンス）。
* **Unknownループ**: 画像が不鮮明な場合、最大5回まで再撮影を促します。
* *ユーザーへのアドバイス例*: 「暗すぎます」「近づきすぎています」「全体を入れてください」



### Phase 2: 特注品・一点物フロー

「AIの限界をユーザーの知識で補う」フェーズです。

* **判定基準**: 型番が存在しないもの（絵画、壺、ハンドメイド家具など）。
* **ドラフト機能**: AIは勝手に決めつけず、「予測」を表示してユーザーに修正させます。
* `素材: [ 木材 (予測) ]` → ユーザーが `[ 黒檀 ]` に修正。


* **Proxy Search**: 修正されたスペックを元に、類似品や素材原価を検索します。

### Phase 3: 既製品フロー（質問制限付き）

「効率的に特定し、夢（可能性）を残す」フェーズです。

* **動的スキーマ**: 検索結果から「価格が変わるポイント」だけをNode Aに見させます。
* **質問制限 (Max 2)**: ユーザー体験を損なわないよう、質問は2回までとします。
* **可能性ヒント (Upside Hint)**:
* 特定しきれなかった場合、ただ「分かりません」とは言いません。
* **「現状は5,000円ですが、もし〇〇（例：初版マーク）があれば、最大150,000円になる可能性があります」** と伝え、ユーザーに再確認のモチベーション（お宝探し感）を提供して終了します。



---

## 3. 重要データのJSONスキーマ

実装時にバックエンド（Lambda等）で扱う主要なJSON構造です。

### A. Vision初期判定 (Node A Output)

```json
{
  "category_type": "mass_product", // mass_product | unique_item | unknown | prohibited
  "item_name": "Pokemon Card Charizard",
  "guardrail_reason": null, // prohibitedの場合に理由が入る
  "retry_advice": null // unknownの場合に「もっと明るく」等が入る
}

```

### B. 最終回答データ (Result Output)

特に `upside_potential` オブジェクトが重要です。

```json
{
  "status": "complete_with_hint", // complete | complete_with_hint | error
  "valuation": {
    "min_price": 5000,
    "max_price": 10000,
    "currency": "JPY",
    "confidence": "medium"
  },
  "display_message": "状態Bランクの一般的な中古相場です。",
  
  // ▼ ここが「可能性ヒント」のためのデータ
  "upside_potential": {
    "has_potential": true,
    "trigger_factor": "No Rarity Symbol (First Edition)", // 何があれば高いか
    "potential_max_price": 150000,
    "user_message": "今回は確認できませんでしたが、もし右下に『マークがない』場合は初版となり、最大15万円前後の可能性があります。"
  }
}

```

この設計により、**「技術的な実現可能性」**と**「ユーザー体験（わくわく感・納得感）」**の両立が可能になります。