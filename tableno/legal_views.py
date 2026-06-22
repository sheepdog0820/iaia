from django.conf import settings
from django.shortcuts import render


DEFAULT_SELLER_NAME = 'タブレノ運営'
DEFAULT_DISCLOSURE_ON_REQUEST = '請求があった場合、遅滞なく開示します。'
DEFAULT_PRICE_LABEL = '月額480円 / 年額4,800円'
DEFAULT_PAYMENT_METHOD = 'Stripe Checkoutで利用可能なクレジットカード等の決済手段。'
DEFAULT_PAYMENT_TIMING = '初回申し込み時に課金され、以後は選択した月額または年額サブスクリプションとして自動更新されます。'
DEFAULT_SERVICE_DELIVERY_TIMING = '決済完了後、Stripe Webhookの処理完了をもってプレミアム機能を利用できます。'
DEFAULT_CANCELLATION_METHOD = 'ログイン後のプレミアム管理画面からStripe Customer Portalへ移動し、いつでも解約できます。'
DEFAULT_CANCELLATION_EFFECT = '解約後も支払い済み期間の終了まではプレミアム機能を利用できます。'

LEGAL_LABELS = {
    'commercial_title': '特定商取引法に基づく表記',
    'seller': '販売事業者',
    'address': '所在地',
    'phone': '電話番号',
    'contact': '問い合わせ先',
    'price': '販売価格',
    'extra_fee': '商品代金以外の必要料金',
    'extra_fee_text': 'インターネット接続料金、通信料等はお客様の負担となります。',
    'payment_method': '支払方法',
    'payment_timing': '支払時期',
    'delivery': '提供時期',
    'cancel_method': '解約方法',
    'cancel_effect': '解約の効力',
    'refund': '返品・キャンセル・返金',
    'environment': '動作環境',
    'environment_text': '最新版の主要ブラウザでの利用を推奨します。',
    'premium_features': 'プレミアム機能',
    'fee': '料金',
    'feature': '機能',
    'free': '無料',
    'premium': 'プレミアム',
    'character': 'キャラクター管理',
    'session': 'セッション管理',
    'archive': 'シナリオアーカイブ',
    'code_use': '運営発行コードの利用',
    'available': '利用可',
    'unavailable': '利用不可',
    'applied': '適用後にプレミアム化',
    'billing_link': 'プレミアム管理へ',
    'signup': '登録して始める',
    'commercial_link': '特定商取引法に基づく表記を見る',
    'summary': '月額料金、支払方法、提供時期、解約方法、返金条件、事業者情報は',
    'listed': 'に記載しています。',
}

DEFAULT_REFUND_POLICY = 'デジタルサービスの性質上、決済完了後のお客様都合による返金は原則として受け付けません。重複請求や誤請求が確認された場合は個別に対応します。'


PREMIUM_FEATURE_ROWS = [
    {
        'key': 'character_management',
        'name': 'キャラクター管理',
        'free': '利用可',
        'premium': '利用可',
        'note': '基本機能として無料で利用できます。',
    },
    {
        'key': 'session_management',
        'name': 'セッション管理',
        'free': '利用可',
        'premium': '利用可',
        'note': '基本機能として無料で利用できます。',
    },
    {
        'key': 'scenario_archive',
        'name': 'シナリオアーカイブ',
        'free': '利用不可',
        'premium': '利用可',
        'note': 'プレミアム限定機能です。',
    },
    {
        'key': 'billing_management',
        'name': '支払い方法・解約管理',
        'free': '-',
        'premium': 'Stripe Customer Portalから利用可',
        'note': '支払い方法更新、解約、請求履歴を管理できます。',
    },
    {
        'key': 'premium_code',
        'name': '運営発行コード',
        'free': '入力可',
        'premium': '適用後にプレミアム化',
        'note': '課金なしで期限付きまたは無期限のプレミアム権限を付与できます。',
    },
]


def terms_view(request):
    return render(request, 'legal/terms.html')


def privacy_view(request):
    return render(request, 'legal/privacy.html')


def contact_view(request):
    return render(request, 'legal/contact.html')


def commercial_disclosure_view(request):
    context = {
        'seller_name': getattr(settings, 'LEGAL_SELLER_NAME', DEFAULT_SELLER_NAME),
        'seller_address': getattr(settings, 'LEGAL_SELLER_ADDRESS', DEFAULT_DISCLOSURE_ON_REQUEST),
        'seller_phone': getattr(settings, 'LEGAL_SELLER_PHONE', DEFAULT_DISCLOSURE_ON_REQUEST),
        'contact_email': getattr(settings, 'CONTACT_EMAIL', 'support@tableno.jp'),
        'premium_price_label': getattr(settings, 'PREMIUM_PRICE_LABEL', DEFAULT_PRICE_LABEL),
        'payment_method': getattr(settings, 'LEGAL_PAYMENT_METHOD', DEFAULT_PAYMENT_METHOD),
        'payment_timing': getattr(settings, 'LEGAL_PAYMENT_TIMING', DEFAULT_PAYMENT_TIMING),
        'service_delivery_timing': getattr(settings, 'LEGAL_SERVICE_DELIVERY_TIMING', DEFAULT_SERVICE_DELIVERY_TIMING),
        'cancellation_method': getattr(settings, 'LEGAL_CANCELLATION_METHOD', DEFAULT_CANCELLATION_METHOD),
        'cancellation_effect': getattr(settings, 'LEGAL_CANCELLATION_EFFECT', DEFAULT_CANCELLATION_EFFECT),
        'refund_policy': getattr(settings, 'LEGAL_REFUND_POLICY', DEFAULT_REFUND_POLICY),
        'labels': LEGAL_LABELS,
    }
    return render(request, 'legal/commercial_disclosure.html', context)


def premium_features_view(request):
    return render(
        request,
        'premium/features.html',
        {
            'premium_price_label': getattr(settings, 'PREMIUM_PRICE_LABEL', DEFAULT_PRICE_LABEL),
            'cancellation_effect': getattr(settings, 'LEGAL_CANCELLATION_EFFECT', DEFAULT_CANCELLATION_EFFECT),
            'payment_timing': getattr(settings, 'LEGAL_PAYMENT_TIMING', DEFAULT_PAYMENT_TIMING),
            'service_delivery_timing': getattr(settings, 'LEGAL_SERVICE_DELIVERY_TIMING', DEFAULT_SERVICE_DELIVERY_TIMING),
            'cancellation_method': getattr(settings, 'LEGAL_CANCELLATION_METHOD', DEFAULT_CANCELLATION_METHOD),
            'refund_policy': getattr(settings, 'LEGAL_REFUND_POLICY', DEFAULT_REFUND_POLICY),
            'labels': LEGAL_LABELS,
            'feature_rows': PREMIUM_FEATURE_ROWS,
        },
    )
