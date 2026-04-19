import html
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter

# --- Page config ---
st.set_page_config(page_title="MIS Coffee Club Smart Dashboard", layout="wide")

# --- Data load ---
FILE_NAME = 'MIS_coffee_dataset.xlsx'

@st.cache_data
def load_all_data():
    try:
        sheets = {
            'tx': pd.read_excel(FILE_NAME, sheet_name='transactions'),
            'items': pd.read_excel(FILE_NAME, sheet_name='transaction_items'),
            'prod': pd.read_excel(FILE_NAME, sheet_name='products'),
            'mem': pd.read_excel(FILE_NAME, sheet_name='members'),
            'ws': pd.read_excel(FILE_NAME, sheet_name='workshops'),
            'taste': pd.read_excel(FILE_NAME, sheet_name='taste_profiles'),
            'recipe': pd.read_excel(FILE_NAME, sheet_name='beverage_bean_recipes'),
            'beverages': pd.read_excel(FILE_NAME, sheet_name='coffee_beverages'),
            'bean': pd.read_excel(FILE_NAME, sheet_name='coffee_beans'),
            'flav': pd.read_excel(FILE_NAME, sheet_name='coffee_flavors'),
            'notes': pd.read_excel(FILE_NAME, sheet_name='flavor_notes'),
            'food': pd.read_excel(FILE_NAME, sheet_name='food'),
            'survey': pd.read_excel(FILE_NAME, sheet_name='game_survey_responses'),
            'feedback': pd.read_excel(FILE_NAME, sheet_name='workshop_feedback')

        }
        return sheets
    except Exception as e:
        st.error(f"❌ Failed to load data: {e}")
        return None

data = load_all_data()
if not data:
    st.stop()


def analyze_ws_strategy(df_ws, df_taste, df_feedback, df_bean):
    market_acidity = df_taste["acidity_score"].mean()
    ws_performance = df_feedback.groupby("workshop_id")["bean_overall_rating"].mean()
    ws_counts = df_feedback.groupby("workshop_id")["member_id"].count()
    recommendations = []
    attendee_list = []
    for _, ws in df_ws.iterrows():
        ws_id = ws["workshop_id"]
        rating = ws_performance.get(ws_id, 0)
        count = ws_counts.get(ws_id, 0)
        attendee_list.append(count)
        try:
            b_id = df_feedback[df_feedback["workshop_id"] == ws_id]["coffee_bean_id"].iloc[0]
            b_acidity = df_bean[df_bean["coffee_bean_id"] == b_id]["acidity"].iloc[0]
        except Exception:
            b_acidity = None
        if rating == 0:
            msg = "🆕 Limited data: new workshop — run acquisition / intro sessions."
        elif rating > 4.5:
            msg = "🔥 Flagship course: very popular — consider premium pricing or extra slots."
        elif b_acidity is not None and market_acidity > 3.5 and b_acidity < 2.5:
            msg = "⚠️ Flavor gap: members lean bright / acidic, but this workshop’s bean reads quite dark."
        elif rating < 3.5:
            msg = "🛠️ Content refresh: ratings are soft — redesign the teaching flow."
        else:
            msg = "✅ Steady performance — keep the current format."
        recommendations.append(msg)
    return recommendations, attendee_list


def calculate_conversion_metrics(df_tx, df_feedback, df_items, df_prod):
    try:
        df_tx = df_tx.copy()
        df_feedback = df_feedback.copy()
        df_tx["transaction_date"] = pd.to_datetime(df_tx["transaction_date"])
        df_feedback["feedback_date"] = pd.to_datetime(
            df_feedback.get("feedback_date", df_tx["transaction_date"].min())
        )
        bean_ids = df_prod[df_prod["category"] == "coffee bean"]["product_id"].unique()
        bean_tx_ids = df_items[df_items["product_id"].isin(bean_ids)]["transaction_id"].unique()
        df_bean_sales = df_tx[df_tx["transaction_id"].isin(bean_tx_ids)][["member_id", "transaction_date"]]
        df_conv = df_feedback[["member_id", "feedback_date"]].merge(df_bean_sales, on="member_id")
        df_after_temp = df_conv[df_conv["transaction_date"] > df_conv["feedback_date"]].copy()
        if not df_after_temp.empty:
            df_after_temp["days_diff"] = (
                df_after_temp["transaction_date"] - df_after_temp["feedback_date"]
            ).dt.days
            days_series = df_after_temp.groupby("member_id")["days_diff"].min()
            return days_series.mean(), days_series.median()
        return 3.5, 3.0
    except Exception:
        return 3.5, 3.0


def draw_radar_chart(member_id, workshop_id, df_taste, df_feedback, df_bean):
    try:
        m_data = df_taste[df_taste["member_id"] == member_id].iloc[0]
        m_values = [
            m_data["acidity_score"],
            m_data["bitterness_score"],
            m_data["roast_score"],
            m_data["body_score"],
            m_data["flavor_fruity_score"] * 5,
        ]
        ws_feedback = df_feedback[df_feedback["workshop_id"] == workshop_id]
        if ws_feedback.empty:
            return go.Figure().update_layout(title="⚠️ No bean data for this workshop")
        ws_bean_id = ws_feedback["coffee_bean_id"].iloc[0]
        b_data = df_bean[df_bean["coffee_bean_id"] == ws_bean_id].iloc[0]
        categories = ["Acidity", "Bitterness", "Roast", "Body", "Fruitiness"]
        roast_map = {"light": 1, "medium": 3, "dark": 5}
        body_map = {"light": 2, "medium": 4, "full": 5}
        b_values = [
            b_data["acidity"],
            b_data["bitterness"],
            roast_map.get(str(b_data["roast_level"]).lower(), 3),
            body_map.get(str(b_data["body"]).lower(), 3),
            4,
        ]
        fig = go.Figure()
        fig.add_trace(
            go.Scatterpolar(
                r=m_values + [m_values[0]],
                theta=categories + [categories[0]],
                fill="toself",
                name="Member preference",
                line_color="rgba(255, 75, 75, 0.8)",
            )
        )
        fig.add_trace(
            go.Scatterpolar(
                r=b_values + [b_values[0]],
                theta=categories + [categories[0]],
                fill="toself",
                name="Workshop bean",
                line_color="rgba(31, 119, 180, 0.8)",
            )
        )
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
            showlegend=True,
            title=f"Flavor match — {b_data['origin']}",
        )
        return fig
    except Exception as e:
        return go.Figure().update_layout(title=f"⚠️ Chart error: {e}")


PAGE_KPIS = "📊  Operational KPIs"
PAGE_VALUE = "🥇  Value coupling & flavor science"
PAGE_DNA = "🧬  Customer taste DNA"
PAGE_WORKSHOP = "🎓  Workshop strategy"
PAGE_OPTIONS = (PAGE_KPIS, PAGE_VALUE, PAGE_DNA, PAGE_WORKSHOP)

NAV_SESSION_KEY = "sidebar_nav_page"


def inject_sidebar_nav_css():
    """Sidebar vertical nav: text row for active page + button rows for others (no radio / red dot)."""
    st.markdown(
        """
        <style>
        /* ---- Sidebar layout (colours follow Streamlit theme) ---- */
        section[data-testid="stSidebar"] {
            width: 280px !important;
            min-width: 260px !important;
        }
        /* Current page row (markdown) */
        section[data-testid="stSidebar"] div.sidebar-nav-active {
            display: flex;
            align-items: center;
            gap: 0.65rem;
            margin: 0 -1rem;
            padding: 0.65rem 1rem;
            border-radius: 6px;
            font-weight: 600;
            line-height: 1.35;
            background-color: var(--secondary-background-color);
        }
        /* Nav buttons: text row, full width, no “primary” red accent */
        section[data-testid="stSidebar"] div.stButton > button {
            width: 100% !important;
            justify-content: flex-start !important;
            text-align: left !important;
            border: none !important;
            box-shadow: none !important;
            background-color: transparent !important;
            color: inherit !important;
            font-weight: 500 !important;
            padding: 0.65rem 1rem !important;
            margin: 0 -1rem !important;
            border-radius: 6px !important;
        }
        section[data-testid="stSidebar"] div.stButton > button:hover {
            background-color: rgba(100, 116, 139, 0.14) !important;
            border: none !important;
        }
        [data-theme="dark"] section[data-testid="stSidebar"] div.stButton > button:hover {
            background-color: rgba(255, 255, 255, 0.07) !important;
        }
        section[data-testid="stSidebar"] div.stButton > button:focus {
            box-shadow: none !important;
        }
        section[data-testid="stSidebar"] hr {
            margin: 0.5rem 0 0.75rem 0 !important;
            opacity: 0.35 !important;
        }
        section[data-testid="stSidebar"] h1 {
            font-size: 1.2rem !important;
            font-weight: 700 !important;
            padding-bottom: 0.15rem !important;
            margin-bottom: 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_operational_kpis(df_tx, df_items, df_prod, df_mem, df_feedback):
    st.header("📊 1. Operational KPIs")
    
    # Pre-compute KPI inputs
    # A. Revenue & AOV
    total_rev = df_tx['total_amount'].sum()
    total_orders = len(df_tx)
    aov = total_rev / total_orders if total_orders > 0 else 0
    
    # B. Attach rate (beverage + food in same order)
    merged_items = df_items.merge(df_prod[['product_id', 'category']], on='product_id')
    order_groups = merged_items.groupby('transaction_id')['category'].unique()
    attach_count = order_groups.apply(lambda x: 'coffee beverage' in x and 'food' in x).sum()
    attach_rate = (attach_count / total_orders * 100) if total_orders > 0 else 0

    # C. Peak hour
    df_tx['transaction_date'] = pd.to_datetime(df_tx['transaction_date'])
    peak_hour = df_tx['transaction_date'].dt.hour.mode()[0]

    # D. Workshop attendees who also bought beans
    ws_members = set(df_feedback['member_id'].unique())
    bean_product_ids = df_prod[df_prod['category'] == 'coffee bean']['product_id'].tolist()
    bean_buyers = set(df_tx[df_tx['transaction_id'].isin(
        df_items[df_items['product_id'].isin(bean_product_ids)]['transaction_id']
    )]['member_id'].unique())
    
    conversion_count = len(ws_members.intersection(bean_buyers))
    ws_conv_rate = (conversion_count / len(ws_members) * 100) if len(ws_members) > 0 else 0

    # KPI row layout
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total revenue", f"${total_rev:,.0f}")
    col2.metric("Average order value (AOV)", f"${aov:.1f}")
    col3.metric("Total orders", f"{total_orders:,}")
    col4.metric("Active members", len(df_mem))

    st.write("")

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Attach rate (beverage + food)", f"{attach_rate:.1f}%", help="Share of orders that include both a beverage and food")
    col6.metric("Peak hour", f"{peak_hour}:00", help="Hour with the most orders")
    col7.metric("Workshop → bean conversion", f"{ws_conv_rate:.1f}%", help="Members who attended a workshop and later bought beans")
    col8.metric("Avg. bean rating", f"{df_feedback['bean_overall_rating'].mean():.1f} / 5.0")

    hourly_sales = df_tx.groupby(df_tx['transaction_date'].dt.hour)['total_amount'].count()
    fig_hour = px.line(
        x=hourly_sales.index,
        y=hourly_sales.values,
        title="Orders by hour of day",
        labels={"x": "Hour", "y": "Orders"},
    )
    st.plotly_chart(fig_hour, use_container_width=True)


    # Rankings data prep
    df_rank = df_items.merge(df_prod[['product_id', 'name', 'category']], on='product_id', how='left')
    product_sales = df_rank.groupby(['name', 'category'])['quantity'].sum().reset_index()

    st.write("### 🏆 Product sales ranking (best vs. weakest)")

    # Category keys must match Excel (lowercased after cleaning)
    categories = {
        "coffee beverage": "☕ Beverages",
        "food": "🍰 Food",
        "coffee bean": "🫘 Beans",
    }

    cols = st.columns(3)

    for i, (cat_key, cat_label) in enumerate(categories.items()):
        with cols[i]:
            st.subheader(cat_label)
            
            # Filter by category
            cat_data = product_sales[product_sales['category'] == cat_key].sort_values('quantity', ascending=False)
            
            if not cat_data.empty:
                # --- Top 3 ---
                st.success("**Top sellers (Top 3)**")
                for _, row in cat_data.head(3).iterrows():
                    st.write(f"🥇 **{row['name']}**")
                    st.caption(f"Units sold: {int(row['quantity'])}")
                
                st.divider()
                
                st.error("**Weakest sellers (Bottom 3)**")
                for _, row in cat_data.tail(3).iloc[::-1].iterrows():
                    st.write(f"⚠️ **{row['name']}**")
                    st.caption(f"Units sold: {int(row['quantity'])}")
            else:
                st.warning(f"No rows for category “{cat_key}”.")
                st.info(f"Categories in data: {df_prod['category'].unique()}")

    st.subheader("🎯 Category funnel (member journey)")
    
    # A. Line items with member id
    df_path = df_items.merge(df_tx[['transaction_id', 'member_id']], on='transaction_id')
    df_path = df_path.merge(df_prod[['product_id', 'category']], on='product_id')

    # B. Member sets per funnel stage
    # Stage 1: bought beverage
    bev_mems = set(df_path[df_path['category'] == 'coffee beverage']['member_id'].unique())
    # Stage 2: beverage + beans
    bean_mems = set(df_path[df_path['category'] == 'coffee bean']['member_id'].unique())
    # Stage 3: beverage + beans + food or equipment (if present)
    equip_mems = set(df_path[df_path['category'].isin(['food', 'equipment'])]['member_id'].unique())

    # C. Funnel counts (set intersections)
    s1_count = len(bev_mems)
    s2_count = len(bev_mems.intersection(bean_mems))
    s3_count = len(bev_mems.intersection(bean_mems).intersection(equip_mems))

    # D. Funnel chart
    fig_funnel = go.Figure(go.Funnel(
        y=["Beverage buyers", "Also bought beans", "Also bought food / equipment"],
        x = [s1_count, s2_count, s3_count],
        textinfo = "value+percent initial",
        textfont = {"size": 20, "color": "white"},
        marker = {"color": ["#D4A373", "#A98467", "#606C38"]}
    ))

    fig_funnel.update_layout(
        margin=dict(l=20, r=20, t=20, b=20),
        height=300
    )

    f_col1, f_col2 = st.columns([2, 1])
    with f_col1:
        st.plotly_chart(fig_funnel, use_container_width=True)
    
    with f_col2:
        st.write("#### 💡 Operations insight")
        if s1_count > 0:
            conv_rate = (s2_count / s1_count) * 100
            st.write(f"**Beverage → bean conversion:** `{conv_rate:.1f}%`")
            if conv_rate < 20:
                st.warning("Bean attach from beverage buyers is low.")
            else:
                st.success("Conversion looks healthy.")

    avg_days, median_days = calculate_conversion_metrics(df_tx, df_feedback, df_items, df_prod)

    st.markdown("---")
    st.write("⏱️ **Conversion speed (workshop → first bean purchase)**")

    if avg_days > median_days:
        dist_type = "Right-skewed (positive skew)"
        insight_text = (
            f"Most learners convert quickly (median only {int(median_days)} days), but a long tail of late buyers pulls the mean up. "
            f"Try a <b>fast-follow</b> campaign with offers 3–5 days after class."
        )
    else:
        dist_type = "Left-skewed (negative skew)"
        insight_text = (
            f"Some buyers convert immediately, but the core group tends to purchase later (median {int(median_days)} days). "
            f"Consider a <b>delayed reminder</b> with offer validity around {int(median_days) + 2} days."
        )

    st.markdown(f"""
        <div style="margin: 20px 0px;">
            <p style="margin: 0;">
                <span style="font-size: 18px; color: #E0E0E0;">Mean days to convert:</span>
                <span style="font-size: 32px; font-weight: bold; color: #D4A373; margin-left: 15px;">{avg_days:.1f} days</span>
            </p>
            <p style="margin: 5px 0px;">
                <span style="font-size: 18px; color: #E0E0E0;">Median days to convert:</span>
                <span style="font-size: 32px; font-weight: bold; color: #A98467; margin-left: 15px;">{int(median_days)} days</span>
            </p>
            <div style="margin-top: 15px; padding: 15px; border-left: 4px solid #D4A373; background-color: rgba(212, 163, 115, 0.1);">
                <p style="margin: 0; font-size: 14px; color: #D4A373; font-weight: bold;">📊 Distribution: {dist_type}</p>
                <p style="margin: 8px 0 0 0; font-size: 15px; color: #AFAFAF; line-height: 1.6;">
                    💡 <b>Playbook:</b> {insight_text}
                </p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")



def render_value_coupling(df_items, df_prod, df_bev, df_recipe, df_bean, df_flav, df_notes, df_food):
    st.header("🥇 2. Value coupling & flavor science")
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("🛒 Market Basket Analysis")
        tx_contents = df_items.merge(df_prod, on='product_id').groupby('transaction_id')['name'].apply(list)
        pair_counts = Counter()
        for items in tx_contents:
            drinks = [i for i in items if df_prod[df_prod['name']==i]['category'].iloc[0] == 'coffee beverage']
            foods = [i for i in items if df_prod[df_prod['name']==i]['category'].iloc[0] == 'food']
            for d in drinks:
                for f in foods: pair_counts[(d, f)] += 1
        
        top_p = pd.DataFrame([{'Pair': f"{k[0]} + {k[1]}", 'Count': v} for k, v in pair_counts.most_common(5)])
        st.plotly_chart(px.bar(top_p, x='Count', y='Pair', orientation='h', color_continuous_scale='Oranges', color='Count'), use_container_width=True)

    with c2:
        st.subheader("🔬 Dynamic flavor pairing")
        coffee_list = df_prod[df_prod['category']=='coffee beverage']['name'].unique()
        selected_drink = st.selectbox("Which beverage did the guest order?", coffee_list, key="value_coupling_drink")
        
        drink_row = df_prod[df_prod['name'] == selected_drink]
        if not drink_row.empty:
            p_id = drink_row['product_id'].iloc[0]
            bev_match = df_bev[df_bev['product_id'] == p_id]
            
            if not bev_match.empty:
                d_id = bev_match['beverage_id'].iloc[0]
                recipe_match = df_recipe[(df_recipe['beverage_id'] == d_id) & (df_recipe['is_default'] == 1)]
                
                if not recipe_match.empty:
                    b_id = recipe_match['coffee_bean_id'].iloc[0]
                    bean_info = df_bean[df_bean['coffee_bean_id'] == b_id].iloc[0]
                    flavs = df_flav[df_flav['coffee_bean_id'] == b_id].merge(df_notes, on='flavor_id')
                    
                    st.write(f"✅ **Bean in recipe:** {bean_info['origin']}")
                    st.write(f"👅 **Flavor notes:** {', '.join(flavs['flavor_name'].tolist())}")
                    
                    # Food pairing
                    food_details = df_food.merge(df_prod[['product_id', 'name']], on='product_id')

                    roast = bean_info['roast_level']
                    acidity = bean_info['acidity']
                    bitterness = bean_info['bitterness']
                    if roast == 'dark' or bitterness >= 4:
                        rec_pool = food_details[(food_details['is_sweet'] == 1) | (food_details['is_rich'] == 1)]
                        reason = "This cup is intense — pair with **sweeter or richer** pastries to balance."
                    elif acidity >= 4 or any(flavs['category'] == 'fruity'):
                        rec_pool = food_details[(food_details['is_flaky'] == 1) | (food_details['is_buttery'] == 1) | (food_details['is_savory'] == 1)]
                        reason = "Bright acidity — **flaky, buttery, or lightly savory** items add contrast."
                    else:
                        rec_pool = food_details[(food_details['is_soft'] == 1) | (food_details['is_moist'] == 1)]
                        reason = "Balanced profile — **soft, moist** bakes complement it well."

                    if not rec_pool.empty:
                        suggestion = rec_pool.sample(n=1).iloc[0]
                        st.success(f"🎯 **Suggested pairing:** {suggestion['name']}")
                        st.info(f"**Why:** {reason}")
                        
                        tag_cols = ['is_sweet', 'is_savory', 'is_flaky', 'is_creamy', 'is_rich']
                        tags = [col.replace('is_','') for col in tag_cols if col in suggestion and suggestion[col] == 1]
                        st.caption(f"💡 Food traits: {' · '.join(tags)}")
                    else:
                        st.write("No suitable pairing found in the current rules.")


    st.markdown("---")



def render_customer_taste_dna(df_tx, df_items, df_prod, df_mem, df_taste, df_survey):
    st.header("🧬 3. Customer taste DNA")

    st.subheader("📊 All members — taste segments")
    col_a, col_b = st.columns([2, 1])

    with col_a:
        # Segment by acidity score
        df_taste['segment'] = df_taste['acidity_score'].apply(
            lambda x: "High acidity (bright)" if x > 3.5 else "Balanced / rich"
        )
        seg_counts = df_taste['segment'].value_counts()
        fig_pie = px.pie(values=seg_counts.values, names=seg_counts.index, 
                        hole=0.4,
                        color_discrete_sequence=['#D4A373', '#606C38'])
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_b:
        st.write("#### 💡 Marketing tip")
        top_seg = seg_counts.idxmax()
        st.info(
            f"Largest segment: **{top_seg}**. Consider featuring that flavor profile in next month’s bean subscription."
        )


    st.subheader("📊 Single member profile")
    search_id = st.number_input("Enter Member ID:", min_value=1, value=1, key="taste_dna_member_id")
    
    # Member / profile lookup
    member = df_mem[df_mem['member_id'] == search_id]
    profile = df_taste[df_taste['member_id'] == search_id]
    survey = df_survey[df_survey['member_id'] == search_id]

    if not member.empty:
        l, r = st.columns([1, 1])
        with l:
            st.subheader(f"👤 {member['name'].values[0]}")
            if not profile.empty:
                categories = ['Roast', 'Body', 'Acidity', 'Bitterness', 'Fruity', 'Sweet']
                values = [profile['roast_score'].values[0], profile['body_score'].values[0], 
                          profile['acidity_score'].values[0], profile['bitterness_score'].values[0],
                          profile['flavor_fruity_score'].values[0]*5, profile['flavor_sweet_score'].values[0]*5]
                fig = go.Figure(data=go.Scatterpolar(r=values, theta=categories, fill='toself', line_color='#6F4E37'))
                fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
        with r:
            st.info("**Customer Persona:** " + ("🔥 Dark Roast Fan" if profile['roast_score'].values[0] > 3 else "🍋 Fruity Explorer"))
            st.subheader("🎮 Game Insights")
            if not survey.empty:
                st.write(f"• Texture: {survey['texture_response'].values[0]}")
                st.write(f"• Weather: {survey['weather_response'].values[0]}")
            
            st.subheader("🛍️ Recent History")
            m_tx = df_tx[df_tx['member_id'] == search_id]['transaction_id']
            history = df_items[df_items['transaction_id'].isin(m_tx)].merge(df_prod, on='product_id')['name'].value_counts().head(3)
            st.write(history if not history.empty else "No records")

        # Staff talking point
        pref = survey["texture_response"].values[0] if not survey.empty else "fuller-bodied"
        st.success(
            f"💬 **Staff script:** “You often enjoy a **{pref}** mouthfeel — want to try today’s pairing pick?”"
        )

    st.markdown("---")



def render_workshop_strategy(data, df_tx, df_items, df_prod, df_mem, df_ws, df_taste, df_feedback, df_bean):
    st.header("🎓 4. Workshop Strategy")
    
    # Workshop feedback frame
    df_fb = data.get("feedback", pd.DataFrame())

    t1, t2, t3 = st.tabs(["📊 Performance", "🎯 Taste matching", "📅 Scheduling & sales"])

    with t1:
        st.subheader("Workshop performance review")
        if not df_fb.empty:
            fb_analysis = df_fb.merge(df_ws, on='workshop_id')
            instructor_perf = fb_analysis.groupby('instructor')['bean_overall_rating'].mean().sort_values(ascending=False)
            
            c1, c2 = st.columns([1, 2])
            with c1:
                st.write("**🏆 Instructor ratings (avg.)**")
                st.dataframe(instructor_perf)
            with c2:
                bitter_issues = fb_analysis[fb_analysis['bitterness_perception'] == 'too_high']
                if not bitter_issues.empty:
                    bitter_counts = bitter_issues['name'].value_counts().reset_index()
                    bitter_counts.columns = ['workshop_name', 'total_count']

                    fig = px.bar(
                        bitter_counts, 
                        x='workshop_name', 
                        y='total_count', 
                        title="Workshops where bitterness felt “too high”",
                        labels={'total_count': 'Responses', 'workshop_name': 'Workshop'},
                        color='total_count',
                        color_continuous_scale='Reds'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.success("✅ No “bitterness too high” pattern in the current feedback.")
        else:
            st.info("No workshop feedback loaded for this view.")

    with t2:
        st.subheader("🎯 Member ↔ workshop taste matching")
        
        c_search1, c_search2 = st.columns(2)
        with c_search1:
            selected_member = st.selectbox("Member ID", df_mem['member_id'].unique(), key="ws_member_lookup")
        
        # Reset cached recommendation when member changes
        if "last_member_id" not in st.session_state or st.session_state.last_member_id != selected_member:
            st.session_state.last_member_id = selected_member
            st.session_state.current_recommendation = None

        m_profile_df = df_taste[df_taste['member_id'] == selected_member]
        
        if not m_profile_df.empty:
            m_profile = m_profile_df.iloc[0]
            st.write(f"👤 **{df_mem[df_mem['member_id'] == selected_member]['name'].iloc[0]}** — taste profile")
            
            cols = st.columns(4)
            cols[0].metric("Acidity preference", f"{m_profile['acidity_score']}/5")
            cols[1].metric("Bitterness preference", f"{m_profile['bitterness_score']}/5")
            cols[2].metric("Roast preference", f"{m_profile['roast_score']}/5")
            cols[3].metric("Fruitiness preference", f"{(m_profile['flavor_fruity_score']*5):.1f}/5")

            st.divider()

            # Score workshops vs member profile
            if st.session_state.current_recommendation is None:
                all_recs = []
                for _, ws in df_ws.iterrows():
                    try:
                        # Bean used in workshop (from first feedback row)
                        ws_feedback_sample = df_feedback[df_feedback['workshop_id'] == ws['workshop_id']]
                        
                        if not ws_feedback_sample.empty:
                            b_id = ws_feedback_sample['coffee_bean_id'].iloc[0]
                            b_data = df_bean[df_bean['coffee_bean_id'] == b_id].iloc[0]
                            
                            # Similarity score
                            diff_acidity = abs(m_profile['acidity_score'] - b_data['acidity'])
                            diff_bitter = abs(m_profile['bitterness_score'] - b_data['bitterness'])
                            
                            # Roast level mapped to 1–5
                            roast_map = {'light': 1, 'medium': 3, 'dark': 5}
                            b_roast_val = roast_map.get(str(b_data["roast_level"]).lower(), 3)
                            diff_roast = abs(m_profile['roast_score'] - b_roast_val)
                            
                            # Penalize large gaps (~10% per combined point)
                            score = max(0, int(100 - ((diff_acidity + diff_bitter + diff_roast) * 10)))
                            
                            all_recs.append({'ws': ws, 'score': score, 'bean': b_data})
                    except Exception as e:
                        continue
                    
                if all_recs:
                    # Pick best score
                    st.session_state.current_recommendation = sorted(all_recs, key=lambda x: x['score'], reverse=True)[0]


            # Radar comparison
            st.write("### 🔍 Deep comparison")
            ws_options = df_ws['name'].tolist()
            try:
                default_idx = ws_options.index(st.session_state.current_recommendation["ws"]["name"])
            except Exception:
                default_idx = 0

            with c_search2:
                compare_ws_name = st.selectbox("Compare with workshop", ws_options, index=default_idx, key="ws_compare_select")
            
            compare_ws_id = df_ws[df_ws['name'] == compare_ws_name]['workshop_id'].iloc[0]
            st.plotly_chart(
                draw_radar_chart(selected_member, compare_ws_id, df_taste, df_feedback, df_bean),
                use_container_width=True,
            )

            # Recommendation card
            st.write("---")
            if st.session_state.current_recommendation:
                rec = st.session_state.current_recommendation
                ws, score, bean = rec['ws'], rec['score'], rec['bean']

                if score >= 85:
                    tag = "🌟 Strong match"
                    desc = f"This workshop fits you well. The **{bean['origin']}** bean aligns about **{score}%** with your usual taste."
                elif score >= 65:
                    edge = "brighter / more acidic" if bean["acidity"] > 3 else "deeper / bolder"
                    tag = "🚀 Stretch match"
                    desc = f"Match score **{score}%**. Expect a cup that leans **{edge}** than your day-to-day orders."
                else:
                    tag = "🧗 Skill stretch"
                    desc = f"Match score **{score}%** — still a useful technical challenge if the guest wants to grow."

                st.subheader(tag)
                st.success(f"### {ws['name']}")
                
                st.write(f"**Flavor match score:** {score}%")
                st.progress(score / 100)
                st.info(f"**💡 Why:**\n{desc}")
                
                if st.button("🔄 Recalculate match"):
                    st.session_state.current_recommendation = None
                    st.rerun()

    with t3:
        if not df_feedback.empty and not df_bean.empty:
            recs, counts = analyze_ws_strategy(df_ws, df_taste, df_feedback, df_bean)
            df_ws_strategy = df_ws.copy()
            df_ws_strategy["strategy_insight"] = recs
            df_ws_strategy["attendees"] = counts
            st.write("### 📊 Workshop performance & strategy")
            st.dataframe(
                df_ws_strategy[["name", "instructor", "attendees", "strategy_insight"]],
                use_container_width=True,
                hide_index=True,
            )

        df_tx["transaction_date"] = pd.to_datetime(df_tx["transaction_date"])
        df_ws["workshop_date"] = pd.to_datetime(df_ws["workshop_date"])
        df_ws_info = df_ws[["workshop_id", "name", "workshop_date"]].rename(columns={"name": "course_full_name"})
        df_ws_events = df_feedback[["member_id", "workshop_id"]].merge(df_ws_info, on="workshop_id")
        df_all_sales = df_items.merge(
            df_tx[["transaction_id", "member_id", "transaction_date"]], on="transaction_id"
        )
        df_all_sales = df_all_sales.merge(df_prod[["product_id", "name", "category"]], on="product_id")
        df_all_sales = df_all_sales.rename(columns={"name": "product_name"})
        df_conversion_track = df_all_sales.merge(df_ws_events, on="member_id")
        df_conversions = df_conversion_track[
            (df_conversion_track["transaction_date"] >= df_conversion_track["workshop_date"])
            & (
                df_conversion_track["transaction_date"]
                <= df_conversion_track["workshop_date"] + pd.Timedelta(days=30)
            )
            & (df_conversion_track["category"] == "coffee bean")
        ].copy()

        st.write("### 🛍️ Workshop-linked bean sales (30-day window)")

        if not df_conversions.empty:
            res = (
                df_conversions.groupby(["course_full_name", "product_name"])
                .size()
                .reset_index(name="sales_count")
            )
            top_selling_data = res.sort_values("sales_count", ascending=False).drop_duplicates("course_full_name")

            def get_intensity(count):
                if count >= 10:
                    return "🔥 High"
                if count >= 5:
                    return "✅ Steady"
                return "⚠️ Needs lift"

            top_selling_data["conversion_strength"] = top_selling_data["sales_count"].apply(get_intensity)
            top_selling_data = top_selling_data.rename(
                columns={
                    "course_full_name": "Workshop",
                    "product_name": "Top bean SKU",
                    "sales_count": "Units (30d)",
                }
            )[["Workshop", "Top bean SKU", "Units (30d)", "conversion_strength"]]
            st.dataframe(top_selling_data, use_container_width=True, hide_index=True)
        else:
            st.info("💡 No rows yet: no bean purchases within 30 days after these workshops.")

        st.caption(
            "Note: counts are real transactions in the “coffee bean” category within 30 days after each workshop date."
        )

if data:
    df_tx, df_items, df_prod = data['tx'], data['items'], data['prod']
    df_mem, df_ws, df_taste = data['mem'], data['ws'], data['taste']
    df_recipe, df_bean, df_flav = data['recipe'], data['bean'], data['flav']
    df_notes, df_food, df_survey = data['notes'], data['food'], data['survey']
    df_bev = data['beverages']
    df_feedback = data['feedback']

    df_prod["category"] = df_prod["category"].str.strip().str.lower()

    inject_sidebar_nav_css()

    if NAV_SESSION_KEY not in st.session_state:
        st.session_state[NAV_SESSION_KEY] = PAGE_KPIS

    with st.sidebar:
        st.title("☕ MIS Coffee Club")
        st.caption("Staff dashboard")
        st.divider()
        for idx, page in enumerate(PAGE_OPTIONS):
            if page == st.session_state[NAV_SESSION_KEY]:
                st.markdown(
                    f'<div class="sidebar-nav-active">{html.escape(page)}</div>',
                    unsafe_allow_html=True,
                )
            else:
                if st.button(
                    page,
                    key=f"sidebar_nav_btn_{idx}",
                    use_container_width=True,
                    type="secondary",
                ):
                    st.session_state[NAV_SESSION_KEY] = page
                    st.rerun()

    current_page = st.session_state[NAV_SESSION_KEY]

    st.title("☕ MIS Coffee Club — staff dashboard")
    st.markdown("---")
    st.caption(f"Current page: **{current_page}**")

    if current_page == PAGE_KPIS:
        render_operational_kpis(df_tx, df_items, df_prod, df_mem, df_feedback)
    elif current_page == PAGE_VALUE:
        render_value_coupling(df_items, df_prod, df_bev, df_recipe, df_bean, df_flav, df_notes, df_food)
    elif current_page == PAGE_DNA:
        render_customer_taste_dna(df_tx, df_items, df_prod, df_mem, df_taste, df_survey)
    elif current_page == PAGE_WORKSHOP:
        render_workshop_strategy(data, df_tx, df_items, df_prod, df_mem, df_ws, df_taste, df_feedback, df_bean)
