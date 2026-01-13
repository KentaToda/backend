"""
Firestoreクライアントラッパーモジュール

DBアクセス時に自動的にログ出力する設計。
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from firebase_admin import firestore
from google.cloud.firestore import Client
from google.cloud.firestore_v1.collection import CollectionReference

from backend.core.firebase import initialize_firebase
from backend.core.logging import get_logger
from backend.core.storage import storage_client


# 型定義
TerminationPoint = Literal[
    "vision_prohibited",
    "vision_unknown",
    "search_unique",
    "price_complete",
    "price_error",
]
OverallStatus = Literal["completed", "incomplete", "error", "pending_reappraisal"]


class FirestoreClient:
    """Firestoreクライアントのラッパー（自動ログ出力対応）"""

    def __init__(self):
        self._db: Client | None = None
        self._logger = get_logger(__name__)

    @property
    def db(self) -> Client:
        """遅延初期化でFirestoreクライアント取得"""
        if self._db is None:
            initialize_firebase()
            self._db = firestore.client()
            self._logger.info("Firestore client initialized")
        return self._db

    def collection(self, path: str) -> CollectionReference:
        """コレクション参照取得（ログ出力付き）"""
        self._logger.debug(f"Accessing collection: {path}")
        return self.db.collection(path)

    async def get_document(self, collection: str, doc_id: str) -> dict[str, Any] | None:
        """
        ドキュメント取得（ログ出力付き）

        Args:
            collection: コレクション名
            doc_id: ドキュメントID

        Returns:
            ドキュメントデータ、存在しない場合はNone
        """
        self._logger.info(f"GET {collection}/{doc_id}")
        ref = self.db.collection(collection).document(doc_id)
        doc = ref.get()
        if doc.exists:
            self._logger.debug(f"Document found: {collection}/{doc_id}")
            return doc.to_dict()
        self._logger.debug(f"Document not found: {collection}/{doc_id}")
        return None

    async def set_document(
        self,
        collection: str,
        doc_id: str,
        data: dict[str, Any],
        merge: bool = False,
    ) -> None:
        """
        ドキュメント作成/更新（ログ出力付き）

        Args:
            collection: コレクション名
            doc_id: ドキュメントID
            data: 保存するデータ
            merge: Trueの場合、既存データとマージ
        """
        self._logger.info(f"SET {collection}/{doc_id} (merge={merge})")
        ref = self.db.collection(collection).document(doc_id)
        ref.set(data, merge=merge)
        self._logger.debug(f"Document written: {collection}/{doc_id}")

    async def update_document(
        self,
        collection: str,
        doc_id: str,
        data: dict[str, Any],
    ) -> None:
        """
        ドキュメント部分更新（ログ出力付き）

        Args:
            collection: コレクション名
            doc_id: ドキュメントID
            data: 更新するフィールドとその値
        """
        self._logger.info(f"UPDATE {collection}/{doc_id}")
        ref = self.db.collection(collection).document(doc_id)
        ref.update(data)
        self._logger.debug(f"Document updated: {collection}/{doc_id}")

    async def delete_document(self, collection: str, doc_id: str) -> None:
        """
        ドキュメント削除（ログ出力付き）

        Args:
            collection: コレクション名
            doc_id: ドキュメントID
        """
        self._logger.info(f"DELETE {collection}/{doc_id}")
        ref = self.db.collection(collection).document(doc_id)
        ref.delete()
        self._logger.debug(f"Document deleted: {collection}/{doc_id}")

    async def check_connection(self) -> dict[str, Any]:
        """
        Firestore接続テスト

        Returns:
            接続状態を含む辞書
        """
        self._logger.info("Checking Firestore connection...")
        try:
            test_ref = self.db.collection("_health_check").document("test")
            doc = test_ref.get()
            self._logger.info("Firestore connection successful")
            return {
                "status": "connected",
                "document_exists": doc.exists,
            }
        except Exception as e:
            self._logger.error(f"Firestore connection failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
            }

    # ========================================
    # ユーザー管理
    # ========================================

    async def get_or_create_user(
        self,
        user_id: str,
        platform: Literal["web", "ios", "android"] = "web",
    ) -> dict[str, Any]:
        """
        ユーザードキュメントを取得、存在しなければ作成

        Args:
            user_id: Firebase Auth uid
            platform: プラットフォーム種別

        Returns:
            ユーザードキュメントのデータ
        """
        self._logger.info(f"GET_OR_CREATE users/{user_id}")
        user_ref = self.db.collection("users").document(user_id)
        doc = user_ref.get()

        if doc.exists:
            # 既存ユーザー: last_active_at を更新
            user_ref.update({"last_active_at": firestore.SERVER_TIMESTAMP})
            return doc.to_dict()

        # 新規ユーザー作成
        user_data = {
            "uid": user_id,
            "created_at": firestore.SERVER_TIMESTAMP,
            "last_active_at": firestore.SERVER_TIMESTAMP,
            "platform": platform,
            "total_appraisals": 0,
            "account_status": "active",
        }
        user_ref.set(user_data)
        self._logger.info(f"Created new user: {user_id}")
        return user_data

    # ========================================
    # 査定履歴管理
    # ========================================

    def _determine_termination_point(
        self,
        vision_result: Optional[dict],
        search_result: Optional[dict],
        price_result: Optional[dict],
    ) -> TerminationPoint:
        """エージェントの終了ポイントを判定"""
        if vision_result:
            category = vision_result.get("category_type")
            if category == "prohibited":
                return "vision_prohibited"
            if category == "unknown":
                return "vision_unknown"

        if search_result:
            classification = search_result.get("analysis", {}).get("classification")
            if classification == "unique_item":
                return "search_unique"

        if price_result:
            status = price_result.get("status")
            if status == "complete":
                return "price_complete"
            return "price_error"

        return "vision_unknown"  # フォールバック

    def _determine_overall_status(
        self,
        termination_point: TerminationPoint,
    ) -> OverallStatus:
        """全体ステータスを判定"""
        if termination_point in ("price_complete", "search_unique"):
            return "completed"
        if termination_point == "price_error":
            return "error"
        if termination_point in ("vision_prohibited", "vision_unknown"):
            return "incomplete"
        return "incomplete"

    async def save_appraisal(
        self,
        user_id: str,
        vision_result: Optional[dict],
        search_result: Optional[dict] = None,
        price_result: Optional[dict] = None,
        image_path: Optional[str] = None,
        user_comment: Optional[str] = None,
        appraisal_id: Optional[str] = None,
    ) -> str:
        """
        査定結果をFirestoreに保存

        Args:
            user_id: Firebase Auth uid
            vision_result: VisionNodeの出力（dict形式）
            search_result: SearchNodeの出力（dict形式、オプション）
            price_result: PriceNodeの出力（dict形式、オプション）
            image_path: Cloud Storage上の画像パス（オプション）
            user_comment: ユーザーからの補足コメント（オプション）
            appraisal_id: 査定ID（指定しない場合は自動生成）

        Returns:
            作成された査定ドキュメントのID
        """
        # ドキュメントID生成（指定がなければタイムスタンプ + UUID）
        if appraisal_id is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            appraisal_id = f"{timestamp}_{uuid.uuid4().hex[:8]}"

        # 終了ポイントとステータスを判定
        termination_point = self._determine_termination_point(
            vision_result, search_result, price_result
        )
        overall_status = self._determine_overall_status(termination_point)

        # ドキュメント構築
        appraisal_doc: dict[str, Any] = {
            "id": appraisal_id,
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
            "overall_status": overall_status,
            "termination_point": termination_point,
        }

        # 入力情報
        if image_path:
            appraisal_doc["image_path"] = image_path
        if user_comment:
            appraisal_doc["user_comment"] = user_comment

        # Vision Node結果
        if vision_result:
            appraisal_doc["vision"] = {
                "category_type": vision_result.get("category_type"),
                "item_name": vision_result.get("item_name"),
                "visual_features": vision_result.get("visual_features", []),
                "confidence": vision_result.get("confidence"),
                "reasoning": vision_result.get("reasoning"),
                "retry_advice": vision_result.get("retry_advice"),
            }

        # Search Node結果
        if search_result:
            analysis = search_result.get("analysis", {})
            appraisal_doc["search"] = {
                "classification": analysis.get("classification"),
                "confidence": analysis.get("confidence"),
                "reasoning": analysis.get("reasoning"),
                "identified_product": analysis.get("identified_product"),
            }

        # Price Node結果
        if price_result:
            valuation = price_result.get("valuation", {})
            appraisal_doc["price"] = {
                "status": price_result.get("status"),
                "min_price": valuation.get("min_price", 0),
                "max_price": valuation.get("max_price", 0),
                "currency": valuation.get("currency", "JPY"),
                "confidence": valuation.get("confidence"),
                "display_message": price_result.get("display_message"),
                "price_factors": price_result.get("price_factors"),
            }

        # 一点物の場合の追加情報（将来の再査定フロー用）
        if termination_point == "search_unique":
            appraisal_doc["unique_item_details"] = {
                "requires_expert": True,
                "expert_request_status": "none",
            }

        # トランザクションで保存 + カウンター更新
        user_ref = self.db.collection("users").document(user_id)
        appraisal_ref = user_ref.collection("appraisals").document(appraisal_id)

        @firestore.transactional
        def save_in_transaction(transaction):
            # 査定履歴を保存
            transaction.set(appraisal_ref, appraisal_doc)
            # ユーザーの総査定回数をインクリメント
            transaction.update(user_ref, {
                "total_appraisals": firestore.Increment(1),
                "last_active_at": firestore.SERVER_TIMESTAMP,
            })

        transaction = self.db.transaction()
        save_in_transaction(transaction)

        self._logger.info(f"Saved appraisal: users/{user_id}/appraisals/{appraisal_id}")
        return appraisal_id

    def _add_image_url(self, appraisal: dict[str, Any]) -> dict[str, Any]:
        """
        査定データにimage_pathがあれば署名付きURLを追加
        """
        if appraisal.get("image_path"):
            try:
                appraisal["image_url"] = storage_client.get_signed_url(
                    appraisal["image_path"]
                )
            except Exception as e:
                self._logger.warning(f"Failed to generate signed URL: {e}")
        return appraisal

    async def get_appraisal_history(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        ユーザーの査定履歴を取得

        Args:
            user_id: Firebase Auth uid
            limit: 取得件数（デフォルト20）
            offset: スキップ件数（デフォルト0）

        Returns:
            査定履歴のリスト（新しい順、image_url付き）
        """
        self._logger.info(f"GET appraisal history: users/{user_id}/appraisals")

        query = (
            self.db.collection("users")
            .document(user_id)
            .collection("appraisals")
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .offset(offset)
        )

        docs = query.stream()
        appraisals = [doc.to_dict() for doc in docs]

        # 署名付きURLを追加
        return [self._add_image_url(a) for a in appraisals]

    async def get_appraisal(
        self,
        user_id: str,
        appraisal_id: str,
    ) -> Optional[dict[str, Any]]:
        """
        特定の査定結果を取得

        Args:
            user_id: Firebase Auth uid
            appraisal_id: 査定ドキュメントID

        Returns:
            査定ドキュメントのデータ（image_url付き）、存在しない場合はNone
        """
        self._logger.info(f"GET users/{user_id}/appraisals/{appraisal_id}")

        doc = (
            self.db.collection("users")
            .document(user_id)
            .collection("appraisals")
            .document(appraisal_id)
            .get()
        )

        if doc.exists:
            appraisal = doc.to_dict()
            return self._add_image_url(appraisal)
        return None


# シングルトンインスタンス
firestore_client = FirestoreClient()
